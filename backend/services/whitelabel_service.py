"""
TradePost Pro - ホワイトラベルサービス
他社ブランドとしてOEM提供するための設定・管理モジュール
"""

import os
import json
import hashlib
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List


@dataclass
class BrandConfig:
    """ブランド設定"""
    brand_id: str = ""
    company_name: str = "TradePost Pro"
    service_name: str = "TradePost Pro"
    logo_url: str = ""
    favicon_url: str = ""
    primary_color: str = "#6366f1"
    secondary_color: str = "#8b5cf6"
    accent_color: str = "#10b981"
    text_color: str = "#ffffff"
    background_color: str = "#0f172a"
    font_family: str = "Noto Sans JP"
    custom_domain: str = ""
    support_email: str = ""
    support_url: str = ""
    terms_url: str = ""
    privacy_url: str = ""
    footer_text: str = ""
    custom_css: str = ""
    # 画像テンプレート設定
    watermark_text: str = ""
    watermark_position: str = "bottom_right"  # top_left, top_right, bottom_left, bottom_right
    hide_powered_by: bool = False
    # メール設定
    email_from_name: str = "TradePost Pro"
    email_from_address: str = ""
    email_header_color: str = "#6366f1"
    # SNS設定
    default_hashtags: List[str] = field(default_factory=list)
    default_footer_text: str = ""


@dataclass
class WhiteLabelTenant:
    """ホワイトラベルテナント"""
    tenant_id: str = ""
    owner_user_id: str = ""
    brand: BrandConfig = field(default_factory=BrandConfig)
    max_users: int = 100
    commission_rate: float = 0.3  # 30%のレベニューシェア
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""
    allowed_plans: List[str] = field(default_factory=lambda: ["light", "standard", "premium"])
    custom_plans: List[Dict] = field(default_factory=list)


class WhiteLabelService:
    """ホワイトラベル管理サービス"""

    def __init__(self):
        self.tenants: Dict[str, WhiteLabelTenant] = {}
        self.domain_map: Dict[str, str] = {}  # domain -> tenant_id

    def create_tenant(
        self,
        owner_user_id: str,
        company_name: str,
        service_name: str,
        custom_domain: str = "",
        **kwargs
    ) -> WhiteLabelTenant:
        """新規テナント作成"""
        tenant_id = hashlib.md5(
            f"{owner_user_id}:{company_name}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        brand = BrandConfig(
            brand_id=tenant_id,
            company_name=company_name,
            service_name=service_name,
            custom_domain=custom_domain,
            **{k: v for k, v in kwargs.items() if hasattr(BrandConfig, k)}
        )

        tenant = WhiteLabelTenant(
            tenant_id=tenant_id,
            owner_user_id=owner_user_id,
            brand=brand,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        self.tenants[tenant_id] = tenant
        if custom_domain:
            self.domain_map[custom_domain] = tenant_id

        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[WhiteLabelTenant]:
        """テナント取得"""
        return self.tenants.get(tenant_id)

    def get_tenant_by_domain(self, domain: str) -> Optional[WhiteLabelTenant]:
        """ドメインからテナント取得"""
        tenant_id = self.domain_map.get(domain)
        if tenant_id:
            return self.tenants.get(tenant_id)
        return None

    def update_brand(self, tenant_id: str, **kwargs) -> Optional[BrandConfig]:
        """ブランド設定更新"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return None

        for key, value in kwargs.items():
            if hasattr(tenant.brand, key):
                setattr(tenant.brand, key, value)

        # ドメイン変更時のマッピング更新
        if "custom_domain" in kwargs:
            old_domains = [d for d, t in self.domain_map.items() if t == tenant_id]
            for d in old_domains:
                del self.domain_map[d]
            if kwargs["custom_domain"]:
                self.domain_map[kwargs["custom_domain"]] = tenant_id

        tenant.updated_at = datetime.now().isoformat()
        return tenant.brand

    def add_custom_plan(
        self,
        tenant_id: str,
        plan_name: str,
        price: int,
        max_sns: int,
        features: Dict
    ) -> bool:
        """カスタムプラン追加"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return False

        custom_plan = {
            "plan_id": f"{tenant_id}_{plan_name.lower().replace(' ', '_')}",
            "name": plan_name,
            "price": price,
            "max_sns": max_sns,
            "features": features,
            "created_at": datetime.now().isoformat(),
        }
        tenant.custom_plans.append(custom_plan)
        tenant.updated_at = datetime.now().isoformat()
        return True

    def generate_css(self, tenant_id: str) -> str:
        """テナント用カスタムCSSを生成"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return ""

        brand = tenant.brand
        css = f"""
:root {{
    --brand-primary: {brand.primary_color};
    --brand-secondary: {brand.secondary_color};
    --brand-accent: {brand.accent_color};
    --brand-text: {brand.text_color};
    --brand-bg: {brand.background_color};
    --brand-font: '{brand.font_family}', sans-serif;
}}

body {{
    font-family: var(--brand-font);
    background-color: var(--brand-bg);
    color: var(--brand-text);
}}

.btn-primary {{
    background-color: var(--brand-primary);
}}

.btn-primary:hover {{
    background-color: var(--brand-secondary);
}}

.accent {{
    color: var(--brand-accent);
}}

.navbar, .sidebar {{
    background-color: var(--brand-primary);
}}

{brand.custom_css}
"""
        return css.strip()

    def generate_image_config(self, tenant_id: str) -> Dict:
        """テナント用画像生成設定を取得"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return {}

        brand = tenant.brand
        return {
            "service_name": brand.service_name,
            "primary_color": brand.primary_color,
            "secondary_color": brand.secondary_color,
            "accent_color": brand.accent_color,
            "text_color": brand.text_color,
            "background_color": brand.background_color,
            "watermark_text": brand.watermark_text or brand.service_name,
            "watermark_position": brand.watermark_position,
            "hide_powered_by": brand.hide_powered_by,
            "logo_url": brand.logo_url,
            "default_hashtags": brand.default_hashtags,
            "footer_text": brand.default_footer_text,
        }

    def generate_email_config(self, tenant_id: str) -> Dict:
        """テナント用メール設定を取得"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return {}

        brand = tenant.brand
        return {
            "from_name": brand.email_from_name or brand.service_name,
            "from_address": brand.email_from_address,
            "header_color": brand.email_header_color,
            "service_name": brand.service_name,
            "company_name": brand.company_name,
            "support_email": brand.support_email,
            "support_url": brand.support_url,
        }

    def calculate_revenue_share(self, tenant_id: str, gross_revenue: float) -> Dict:
        """レベニューシェア計算"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return {}

        platform_share = gross_revenue * (1 - tenant.commission_rate)
        tenant_share = gross_revenue * tenant.commission_rate

        return {
            "gross_revenue": gross_revenue,
            "commission_rate": tenant.commission_rate,
            "platform_share": round(platform_share, 2),
            "tenant_share": round(tenant_share, 2),
        }

    def export_tenant_config(self, tenant_id: str) -> Optional[str]:
        """テナント設定をJSON形式でエクスポート"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return None
        return json.dumps(asdict(tenant), ensure_ascii=False, indent=2)

    def get_all_tenants(self) -> List[WhiteLabelTenant]:
        """全テナント一覧"""
        return list(self.tenants.values())

    def deactivate_tenant(self, tenant_id: str) -> bool:
        """テナント無効化"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return False
        tenant.is_active = False
        tenant.updated_at = datetime.now().isoformat()
        return True


# テスト用
if __name__ == "__main__":
    service = WhiteLabelService()

    # テナント作成
    tenant = service.create_tenant(
        owner_user_id="user_001",
        company_name="FX Trading Corp",
        service_name="FX AutoPost",
        custom_domain="autopost.fxtrading.com",
        primary_color="#ff6b00",
        secondary_color="#ff9500",
    )
    print(f"テナント作成: {tenant.tenant_id}")
    print(f"ブランド名: {tenant.brand.service_name}")

    # CSS生成
    css = service.generate_css(tenant.tenant_id)
    print(f"\nCSS生成: {len(css)}文字")

    # 画像設定
    img_config = service.generate_image_config(tenant.tenant_id)
    print(f"画像設定: {img_config['service_name']}")

    # レベニューシェア
    share = service.calculate_revenue_share(tenant.tenant_id, 100000)
    print(f"\nレベニューシェア (売上: ¥{share['gross_revenue']:,.0f})")
    print(f"  プラットフォーム: ¥{share['platform_share']:,.0f}")
    print(f"  テナント: ¥{share['tenant_share']:,.0f}")

    # カスタムプラン
    service.add_custom_plan(
        tenant.tenant_id,
        "Enterprise",
        price=9800,
        max_sns=5,
        features={"video": True, "custom_template": True, "priority_support": True}
    )
    print(f"\nカスタムプラン数: {len(tenant.custom_plans)}")
    print("✓ ホワイトラベルサービス テスト完了")
