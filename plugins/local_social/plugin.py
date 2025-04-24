from collections import defaultdict
from pathlib import Path

from material.plugins.social.plugin import SocialPlugin as OrigSocialPlugin


class LocalSocialPlugin(OrigSocialPlugin):

    def _load_font(self, config):
        font_path = self.config.cards_layout_options.get("font_path")

        if isinstance(font_path, dict):
            font_files = font_path

            fonts = {}
            for weight, file_path in font_files.items():
                path = Path(file_path).resolve()
                if path.exists():
                    fonts[weight] = str(path)
                else:
                    print(f"[LocalSocialPlugin] ⚠️ 폰트 없음 ({weight}): {path}")

            if "Regular" in fonts:
                return defaultdict(lambda: fonts["Regular"], fonts)
            else:
                print("[LocalSocialPlugin] ⚠️ Regular 폰트가 없어 기본 폰트로 fallback")

        return super()._load_font(config)

    def _render_card(self, site_name, title, description):
        # 배경 및 로고 렌더링 (기존과 동일)
        image = self._render_card_background((1200, 630), self.color["fill"])
        image.alpha_composite(self._resized_logo_promise.result(), (1200 - 228, 64 - 4))

        # 사이트명 렌더링 (기존과 동일)
        font = self._get_font("Bold", 36)
        image.alpha_composite(self._render_text((826, 48), font, site_name, 1, 20), (64 + 4, 64))

        # 🔧 제목 렌더링: 너비, 폰트 크기, 줄 수 조정
        font = self._get_font("Bold", 72)  # 기존 92 → 72로 줄이기
        image.alpha_composite(self._render_text((1000, 250), font, title, 2, 24), (64, 160))

        # 설명 렌더링 (기존과 동일)
        font = self._get_font("Regular", 28)
        image.alpha_composite(self._render_text((826, 80), font, description, 2, 14), (64 + 4, 512))

        return image
