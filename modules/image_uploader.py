"""
ConoHa オブジェクトストレージ 画像アップロードモジュール
=========================================================
ConoHa 3.0のS3互換API（boto3）を使用して、生成した画像を
オブジェクトストレージにアップロードし、公開URLを取得します。

Instagram, Threads, TikTok, LINEへの画像投稿に必要な
HTTPS公開URLを提供します。

【前提条件】
- ConoHa 3.0のオブジェクトストレージが有効であること
- ACCESS_KEY と SECRET_KEY を取得済みであること
- pip install boto3 でパッケージをインストール済みであること

【使い方】
    from modules.image_uploader import ConoHaImageUploader
    
    uploader = ConoHaImageUploader(
        access_key="...",
        secret_key="...",
        bucket_name="sns-images"
    )
    
    # 画像をアップロードして公開URLを取得
    public_url = uploader.upload("/path/to/image.jpg")
    print(public_url)
"""

import hashlib
import logging
import mimetypes
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)


class ConoHaImageUploader:
    """
    ConoHa 3.0 オブジェクトストレージ（S3互換API）を使用して
    画像をアップロードするクラス。
    """

    # ConoHa 3.0 S3互換エンドポイント
    DEFAULT_ENDPOINT = "https://s3.c3j1.conoha.io"
    DEFAULT_REGION = "conoha"

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        endpoint_url: str = DEFAULT_ENDPOINT,
        region_name: str = DEFAULT_REGION,
        public_base_url: str = ""
    ):
        """
        Args:
            access_key: ConoHa S3 ACCESS_KEY
            secret_key: ConoHa S3 SECRET_KEY
            bucket_name: バケット（コンテナ）名
            endpoint_url: S3互換エンドポイントURL
            region_name: リージョン名
            public_base_url: 公開URLのベースURL（カスタムドメイン使用時）
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.region_name = region_name
        self.public_base_url = public_base_url
        self._client = None

    def _get_client(self):
        """boto3 S3クライアントを取得します。"""
        if self._client is None:
            try:
                import boto3
            except ImportError:
                raise ImportError(
                    "boto3パッケージがインストールされていません。\n"
                    "  pip install boto3"
                )

            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region_name
            )
            logger.info(
                f"ConoHa S3クライアント初期化完了: "
                f"endpoint={self.endpoint_url}, bucket={self.bucket_name}"
            )

        return self._client

    def ensure_bucket_exists(self):
        """
        バケットが存在しない場合は作成します。
        """
        client = self._get_client()

        try:
            client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"バケット '{self.bucket_name}' は既に存在します")
        except Exception:
            logger.info(f"バケット '{self.bucket_name}' を作成します")
            client.create_bucket(Bucket=self.bucket_name)
            logger.info(f"バケット '{self.bucket_name}' を作成しました")

            # パブリック読み取りポリシーの設定
            self._set_public_read_policy()

    def _set_public_read_policy(self):
        """
        バケットにパブリック読み取りポリシーを設定します。
        """
        import json

        client = self._get_client()

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{self.bucket_name}/*"
                }
            ]
        }

        try:
            client.put_bucket_policy(
                Bucket=self.bucket_name,
                Policy=json.dumps(policy)
            )
            logger.info(f"バケットポリシー（パブリック読み取り）を設定しました")
        except Exception as e:
            logger.warning(
                f"バケットポリシーの設定に失敗しました: {e}\n"
                f"ConoHaコントロールパネルから手動で公開設定を行ってください。"
            )

    def upload(
        self,
        file_path: str,
        key: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> str:
        """
        ファイルをオブジェクトストレージにアップロードします。
        
        Args:
            file_path: アップロードするファイルのローカルパス
            key: オブジェクトキー（デフォルト: 日付ベースのパス）
            content_type: Content-Type（デフォルト: 自動判定）
        
        Returns:
            str: アップロードされたファイルの公開URL
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

        # オブジェクトキーの生成
        if key is None:
            date_prefix = datetime.now().strftime("%Y/%m/%d")
            key = f"trade-reports/{date_prefix}/{file_path.name}"

        # Content-Typeの判定
        if content_type is None:
            content_type, _ = mimetypes.guess_type(str(file_path))
            if content_type is None:
                content_type = "application/octet-stream"

        logger.info(f"アップロード開始: {file_path} → {key}")

        client = self._get_client()

        # ファイルの読み込みとチェックサム計算
        with open(file_path, "rb") as f:
            body = f.read()

        checksum_sha256 = hashlib.sha256(body).hexdigest()

        try:
            client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=body,
                ContentType=content_type,
                ChecksumSHA256=checksum_sha256
            )

            # 公開URLの生成
            public_url = self._get_public_url(key)

            logger.info(f"アップロード完了: {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"アップロード失敗: {e}")
            raise

    def upload_from_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str = "image/jpeg"
    ) -> str:
        """
        バイトデータを直接アップロードします。
        
        Args:
            data: アップロードするバイトデータ
            key: オブジェクトキー
            content_type: Content-Type
        
        Returns:
            str: 公開URL
        """
        client = self._get_client()
        checksum_sha256 = hashlib.sha256(data).hexdigest()

        client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
            ChecksumSHA256=checksum_sha256
        )

        public_url = self._get_public_url(key)
        logger.info(f"バイトデータアップロード完了: {public_url}")
        return public_url

    def _get_public_url(self, key: str) -> str:
        """
        オブジェクトの公開URLを生成します。
        
        Args:
            key: オブジェクトキー
        
        Returns:
            str: 公開URL
        """
        if self.public_base_url:
            return f"{self.public_base_url.rstrip('/')}/{key}"

        # ConoHaのデフォルトURL形式
        return f"{self.endpoint_url}/{self.bucket_name}/{key}"

    def delete(self, key: str) -> bool:
        """
        オブジェクトを削除します。
        
        Args:
            key: 削除するオブジェクトキー
        
        Returns:
            bool: 削除成功ならTrue
        """
        try:
            client = self._get_client()
            client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"オブジェクト削除完了: {key}")
            return True
        except Exception as e:
            logger.error(f"オブジェクト削除失敗: {e}")
            return False

    def list_objects(self, prefix: str = "") -> list:
        """
        バケット内のオブジェクト一覧を取得します。
        
        Args:
            prefix: フィルタリング用のプレフィックス
        
        Returns:
            list: オブジェクト情報のリスト
        """
        client = self._get_client()

        params = {"Bucket": self.bucket_name}
        if prefix:
            params["Prefix"] = prefix

        response = client.list_objects_v2(**params)
        objects = response.get("Contents", [])

        return [
            {
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
                "url": self._get_public_url(obj["Key"])
            }
            for obj in objects
        ]


def main():
    """画像アップロードのテスト実行。"""
    from modules.utils import setup_logger
    from config.settings import (
        CONOHA_ACCESS_KEY, CONOHA_SECRET_KEY,
        CONOHA_BUCKET_NAME, CONOHA_ENDPOINT_URL,
        LOG_DIR
    )

    setup_logger("modules.image_uploader", LOG_DIR)

    uploader = ConoHaImageUploader(
        access_key=CONOHA_ACCESS_KEY,
        secret_key=CONOHA_SECRET_KEY,
        bucket_name=CONOHA_BUCKET_NAME,
        endpoint_url=CONOHA_ENDPOINT_URL
    )

    # テスト: バケットの確認
    uploader.ensure_bucket_exists()

    # テスト: 画像のアップロード
    test_image = Path(__file__).resolve().parent.parent / "output" / "trade_report_2026-03-11.jpg"
    if test_image.exists():
        url = uploader.upload(str(test_image))
        print(f"\nアップロード完了: {url}")
    else:
        print(f"テスト画像が見つかりません: {test_image}")


if __name__ == "__main__":
    main()
