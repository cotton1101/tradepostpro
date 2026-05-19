"""
リターゲティングピクセル管理サービス
Facebook Pixel / Google Ads / Google Analytics タグの管理と設置
"""

import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class PixelType(Enum):
    """ピクセルタイプ"""
    FACEBOOK = "facebook"
    GOOGLE_ADS = "google_ads"
    GOOGLE_ANALYTICS = "google_analytics"
    TIKTOK = "tiktok"
    LINE_TAG = "line_tag"


class ConversionEvent(Enum):
    """コンバージョンイベント"""
    PAGE_VIEW = "PageView"
    REGISTRATION = "CompleteRegistration"
    TRIAL_START = "StartTrial"
    SUBSCRIPTION = "Subscribe"
    PURCHASE = "Purchase"
    ADD_TO_CART = "AddToCart"
    LEAD = "Lead"
    CUSTOM = "Custom"


@dataclass
class PixelConfig:
    """ピクセル設定"""
    pixel_type: PixelType
    pixel_id: str
    is_active: bool = True
    events: list = field(default_factory=list)
    custom_params: dict = field(default_factory=dict)


@dataclass
class ConversionTracking:
    """コンバージョントラッキング設定"""
    event: ConversionEvent
    pixel_types: list
    value: Optional[float] = None
    currency: str = "JPY"
    custom_data: dict = field(default_factory=dict)


class RetargetingService:
    """リターゲティングピクセル管理サービス"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.pixels: dict = {}
        self.conversion_rules: list = []

        # デフォルト設定の読み込み
        self._load_default_config()

    def _load_default_config(self):
        """デフォルトのピクセル設定を読み込み"""
        fb_pixel_id = self.config.get("facebook_pixel_id", "")
        google_ads_id = self.config.get("google_ads_id", "")
        ga_measurement_id = self.config.get("ga_measurement_id", "")
        tiktok_pixel_id = self.config.get("tiktok_pixel_id", "")
        line_tag_id = self.config.get("line_tag_id", "")

        if fb_pixel_id:
            self.pixels["facebook"] = PixelConfig(
                pixel_type=PixelType.FACEBOOK,
                pixel_id=fb_pixel_id,
            )
        if google_ads_id:
            self.pixels["google_ads"] = PixelConfig(
                pixel_type=PixelType.GOOGLE_ADS,
                pixel_id=google_ads_id,
            )
        if ga_measurement_id:
            self.pixels["google_analytics"] = PixelConfig(
                pixel_type=PixelType.GOOGLE_ANALYTICS,
                pixel_id=ga_measurement_id,
            )
        if tiktok_pixel_id:
            self.pixels["tiktok"] = PixelConfig(
                pixel_type=PixelType.TIKTOK,
                pixel_id=tiktok_pixel_id,
            )
        if line_tag_id:
            self.pixels["line_tag"] = PixelConfig(
                pixel_type=PixelType.LINE_TAG,
                pixel_id=line_tag_id,
            )

        # デフォルトのコンバージョンルール
        self.conversion_rules = [
            ConversionTracking(
                event=ConversionEvent.REGISTRATION,
                pixel_types=[PixelType.FACEBOOK, PixelType.GOOGLE_ADS, PixelType.GOOGLE_ANALYTICS],
            ),
            ConversionTracking(
                event=ConversionEvent.TRIAL_START,
                pixel_types=[PixelType.FACEBOOK, PixelType.GOOGLE_ADS],
            ),
            ConversionTracking(
                event=ConversionEvent.SUBSCRIPTION,
                pixel_types=[PixelType.FACEBOOK, PixelType.GOOGLE_ADS, PixelType.GOOGLE_ANALYTICS],
                value=2980,
                currency="JPY",
            ),
        ]

    def generate_head_tags(self, user_config: dict = None) -> str:
        """HTMLヘッドに挿入するタグを生成"""
        tags = []

        # Facebook Pixel
        fb_config = self.pixels.get("facebook") or (
            PixelConfig(pixel_type=PixelType.FACEBOOK, pixel_id=user_config.get("facebook_pixel_id", ""))
            if user_config and user_config.get("facebook_pixel_id") else None
        )
        if fb_config and fb_config.pixel_id:
            tags.append(self._generate_facebook_pixel(fb_config.pixel_id))

        # Google Analytics (GA4)
        ga_config = self.pixels.get("google_analytics") or (
            PixelConfig(pixel_type=PixelType.GOOGLE_ANALYTICS, pixel_id=user_config.get("ga_measurement_id", ""))
            if user_config and user_config.get("ga_measurement_id") else None
        )
        if ga_config and ga_config.pixel_id:
            tags.append(self._generate_google_analytics(ga_config.pixel_id))

        # Google Ads
        gads_config = self.pixels.get("google_ads") or (
            PixelConfig(pixel_type=PixelType.GOOGLE_ADS, pixel_id=user_config.get("google_ads_id", ""))
            if user_config and user_config.get("google_ads_id") else None
        )
        if gads_config and gads_config.pixel_id:
            tags.append(self._generate_google_ads(gads_config.pixel_id))

        # TikTok Pixel
        tt_config = self.pixels.get("tiktok") or (
            PixelConfig(pixel_type=PixelType.TIKTOK, pixel_id=user_config.get("tiktok_pixel_id", ""))
            if user_config and user_config.get("tiktok_pixel_id") else None
        )
        if tt_config and tt_config.pixel_id:
            tags.append(self._generate_tiktok_pixel(tt_config.pixel_id))

        # LINE Tag
        line_config = self.pixels.get("line_tag") or (
            PixelConfig(pixel_type=PixelType.LINE_TAG, pixel_id=user_config.get("line_tag_id", ""))
            if user_config and user_config.get("line_tag_id") else None
        )
        if line_config and line_config.pixel_id:
            tags.append(self._generate_line_tag(line_config.pixel_id))

        return "\n".join(tags)

    def generate_conversion_script(self, event: ConversionEvent, value: float = None, currency: str = "JPY") -> str:
        """コンバージョンイベントのスクリプトを生成"""
        scripts = []

        for rule in self.conversion_rules:
            if rule.event != event:
                continue

            for pixel_type in rule.pixel_types:
                ev_value = value or rule.value
                ev_currency = currency or rule.currency

                if pixel_type == PixelType.FACEBOOK and "facebook" in self.pixels:
                    scripts.append(self._fb_conversion_event(event, ev_value, ev_currency))
                elif pixel_type == PixelType.GOOGLE_ADS and "google_ads" in self.pixels:
                    scripts.append(self._gads_conversion_event(event, ev_value, ev_currency))
                elif pixel_type == PixelType.GOOGLE_ANALYTICS and "google_analytics" in self.pixels:
                    scripts.append(self._ga_conversion_event(event, ev_value, ev_currency))

        return "\n".join(scripts)

    def _generate_facebook_pixel(self, pixel_id: str) -> str:
        """Facebook Pixelタグを生成"""
        return f"""<!-- Facebook Pixel -->
<script>
!function(f,b,e,v,n,t,s)
{{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '{pixel_id}');
fbq('track', 'PageView');
</script>
<noscript><img height="1" width="1" style="display:none"
src="https://www.facebook.com/tr?id={pixel_id}&ev=PageView&noscript=1"/></noscript>
<!-- End Facebook Pixel -->"""

    def _generate_google_analytics(self, measurement_id: str) -> str:
        """Google Analytics (GA4) タグを生成"""
        return f"""<!-- Google Analytics (GA4) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', '{measurement_id}');
</script>
<!-- End Google Analytics -->"""

    def _generate_google_ads(self, ads_id: str) -> str:
        """Google Adsリマーケティングタグを生成"""
        return f"""<!-- Google Ads Remarketing -->
<script async src="https://www.googletagmanager.com/gtag/js?id={ads_id}"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', '{ads_id}');
</script>
<!-- End Google Ads Remarketing -->"""

    def _generate_tiktok_pixel(self, pixel_id: str) -> str:
        """TikTok Pixelタグを生成"""
        return f"""<!-- TikTok Pixel -->
<script>
!function (w, d, t) {{
  w.TiktokAnalyticsObject=t;var ttq=w[t]=w[t]||[];ttq.methods=["page","track","identify","instances","debug","on","off","once","ready","alias","group","enableCookie","disableCookie"],ttq.setAndDefer=function(t,e){{t[e]=function(){{t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}}}; for(var i=0;i<ttq.methods.length;i++)ttq.setAndDefer(ttq,ttq.methods[i]);ttq.instance=function(t){{for(var e=ttq._i[t]||[],n=0;n<ttq.methods.length;n++)ttq.setAndDefer(e,ttq.methods[n]);return e}};ttq.load=function(e,n){{var i="https://analytics.tiktok.com/i18n/pixel/events.js";ttq._i=ttq._i||{{}};ttq._i[e]=[];ttq._i[e]._u=i;ttq._t=ttq._t||{{}};ttq._t[e+\"_\"+n]=1;var o=document.createElement("script");o.type="text/javascript";o.async=!0;o.src=i+"?sdkid="+e+"&lib="+t;var a=document.getElementsByTagName("script")[0];a.parentNode.insertBefore(o,a)}};
  ttq.load('{pixel_id}');
  ttq.page();
}}(window, document, 'ttq');
</script>
<!-- End TikTok Pixel -->"""

    def _generate_line_tag(self, tag_id: str) -> str:
        """LINE Tagを生成"""
        return f"""<!-- LINE Tag -->
<script>
(function(g,d,o){{
  g._ltq=g._ltq||[];g._lt=g._lt||function(){{g._ltq.push(arguments)}};
  var h=d.getElementsByTagName(o)[0];
  var s=d.createElement(o);s.async=1;
  s.src='https://d.line-scdn.net/n/line_tag/public/release/v1/lt.js';
  h.parentNode.insertBefore(s,h);
}})(window,document,'script');
_lt('init', {{
  customerType: 'account',
  tagId: '{tag_id}'
}});
_lt('send', 'pv', ['{tag_id}']);
</script>
<noscript>
<img height="1" width="1" style="display:none"
src="https://tr.line.me/tag.gif?c_t=lap&t_id={tag_id}&e=pv&noscript=1"/>
</noscript>
<!-- End LINE Tag -->"""

    def _fb_conversion_event(self, event: ConversionEvent, value: float = None, currency: str = "JPY") -> str:
        """Facebook コンバージョンイベント"""
        event_name = event.value
        if value:
            return f"<script>fbq('track', '{event_name}', {{value: {value}, currency: '{currency}'}});</script>"
        return f"<script>fbq('track', '{event_name}');</script>"

    def _gads_conversion_event(self, event: ConversionEvent, value: float = None, currency: str = "JPY") -> str:
        """Google Ads コンバージョンイベント"""
        event_map = {
            ConversionEvent.REGISTRATION: "sign_up",
            ConversionEvent.TRIAL_START: "start_trial",
            ConversionEvent.SUBSCRIPTION: "purchase",
            ConversionEvent.PURCHASE: "purchase",
        }
        ga_event = event_map.get(event, "custom_event")
        if value:
            return f"<script>gtag('event', '{ga_event}', {{value: {value}, currency: '{currency}'}});</script>"
        return f"<script>gtag('event', '{ga_event}');</script>"

    def _ga_conversion_event(self, event: ConversionEvent, value: float = None, currency: str = "JPY") -> str:
        """Google Analytics コンバージョンイベント"""
        event_map = {
            ConversionEvent.REGISTRATION: "sign_up",
            ConversionEvent.TRIAL_START: "begin_checkout",
            ConversionEvent.SUBSCRIPTION: "purchase",
        }
        ga_event = event_map.get(event, "custom_event")
        if value:
            return f"<script>gtag('event', '{ga_event}', {{value: {value}, currency: '{currency}'}});</script>"
        return f"<script>gtag('event', '{ga_event}');</script>"

    def generate_data_layer_push(self, event_name: str, data: dict) -> str:
        """GTMデータレイヤープッシュを生成"""
        data_json = json.dumps(data, ensure_ascii=False)
        return f"""<script>
window.dataLayer = window.dataLayer || [];
window.dataLayer.push({{
  'event': '{event_name}',
  ...{data_json}
}});
</script>"""

    def get_pixel_status(self) -> dict:
        """全ピクセルのステータスを取得"""
        status = {}
        for key, pixel in self.pixels.items():
            status[key] = {
                "type": pixel.pixel_type.value,
                "id": pixel.pixel_id,
                "is_active": pixel.is_active,
            }
        return status

    def generate_blade_partial(self) -> str:
        """Laravel Blade用のパーシャルテンプレートを生成"""
        return """{{-- resources/views/partials/tracking-pixels.blade.php --}}
@if(config('tracking.facebook_pixel_id'))
<!-- Facebook Pixel -->
<script>
!function(f,b,e,v,n,t,s)
{if(f.fbq)return;n=f.fbq=function(){n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '{{ config("tracking.facebook_pixel_id") }}');
fbq('track', 'PageView');
</script>
@endif

@if(config('tracking.ga_measurement_id'))
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id={{ config('tracking.ga_measurement_id') }}"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', '{{ config("tracking.ga_measurement_id") }}');
</script>
@endif

@if(config('tracking.google_ads_id'))
<!-- Google Ads Remarketing -->
<script async src="https://www.googletagmanager.com/gtag/js?id={{ config('tracking.google_ads_id') }}"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', '{{ config("tracking.google_ads_id") }}');
</script>
@endif
"""


# テスト実行
if __name__ == "__main__":
    config = {
        "facebook_pixel_id": "1234567890",
        "google_ads_id": "AW-1234567890",
        "ga_measurement_id": "G-XXXXXXXXXX",
        "tiktok_pixel_id": "CXXXXXXXXX",
        "line_tag_id": "abcdef12-3456-7890",
    }

    service = RetargetingService(config)

    print("=== ピクセルステータス ===")
    status = service.get_pixel_status()
    for key, info in status.items():
        print(f"  {key}: {info['type']} ({info['id']}) - {'有効' if info['is_active'] else '無効'}")

    print("\n=== ヘッドタグ生成 ===")
    head_tags = service.generate_head_tags()
    print(f"  生成されたタグ長: {len(head_tags)}文字")
    print(f"  Facebook Pixel: {'含む' if 'fbevents.js' in head_tags else '含まない'}")
    print(f"  Google Analytics: {'含む' if 'gtag/js' in head_tags else '含まない'}")
    print(f"  TikTok Pixel: {'含む' if 'tiktok.com' in head_tags else '含まない'}")
    print(f"  LINE Tag: {'含む' if 'line-scdn.net' in head_tags else '含まない'}")

    print("\n=== コンバージョンスクリプト ===")
    reg_script = service.generate_conversion_script(ConversionEvent.REGISTRATION)
    print(f"  登録イベント: {len(reg_script)}文字")

    sub_script = service.generate_conversion_script(ConversionEvent.SUBSCRIPTION, 2980, "JPY")
    print(f"  購読イベント: {len(sub_script)}文字")

    print("\n=== Bladeパーシャル ===")
    blade = service.generate_blade_partial()
    print(f"  テンプレート長: {len(blade)}文字")

    print("\n✓ リターゲティングピクセルサービス テスト完了")
