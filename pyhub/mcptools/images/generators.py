import abc
from typing import Union

import httpx
from django.conf import settings
from PIL.Image import Image as PILImage

from pyhub.mcptools.core.exceptions import APIException
from pyhub.mcptools.images.types import ImageGeneratorVendor
from pyhub.mcptools.images.utils import fetch_image


class ImageGenerator(metaclass=abc.ABCMeta):

    @classmethod
    async def run(
        cls,
        vendor: ImageGeneratorVendor,
        query: str,
        width: int = 1024,
        height: int = 1024,
    ) -> Union[str, PILImage]:
        generator_cls = {
            ImageGeneratorVendor.UNSPLASH: UnsplashImageGenerator,
            ImageGeneratorVendor.TOGETHER_AI: TogetherImageGenerator,
        }[vendor]

        image_gen = generator_cls()
        image_gen.check()
        return await image_gen.make(query, width=width, height=height)

    @abc.abstractmethod
    def check(self) -> None:
        pass

    @abc.abstractmethod
    async def make(self, query: str, width: int = 1024, height: int = 1024) -> PILImage:
        pass


#
# https://unsplash.com/documentation#dynamically-resizable-images
#
# Demo apps are limited to 50 requests per hour. Learn more.
#

# https://api.unsplash.com/photos


class UnsplashImageGenerator(ImageGenerator):
    def check(self) -> None:
        assert settings.UNSPLASH_ACCESS_KEY, "UNSPLASH_ACCESS_KEY 환경변수 누락"
        assert settings.UNSPLASH_SECRET_KEY, "UNSPLASH_SECRET_KEY 환경변수 누락"

    async def make(self, query: str, width: int = 1024, height: int = 1024) -> PILImage:
        async with httpx.AsyncClient() as client:
            if query == "random":
                api_url = "https://api.unsplash.com/photos/random"
            else:
                api_url = "https://api.unsplash.com/search/photos"

            # api.unsplash.com/search/photos?query=canada
            response = await client.get(
                api_url,
                headers={"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"},
                params={"query": query, "per_page": 1},
            )
            response.raise_for_status()
            # TODO: Tool 응답에 반영할 방법은?
            # ratelimit_limit = int(response.headers["x-ratelimit-limit"])
            # ratelimit_remaining = int(response.headers["x-ratelimit-remaining"])
            data = response.json()
            image_url = None

            if "errors" in data:
                error_msg = " ".join(data["errors"])
                raise APIException(error_msg)

            # random
            elif "urls" in data:
                image_urls: dict = data["urls"]
                for quality in ("raw", "full", "regular", "small", "thumb"):
                    if quality in image_urls:
                        image_url = image_urls[quality]
                        break

            # search
            elif "results" in data:
                image_url = data["results"][0]["urls"]["regular"]

            if image_url is None:
                raise APIException("No images found")

            return await fetch_image(image_url)


#
# Together AI, Image Models
#
# https://docs.together.ai/docs/serverless-models#image-models
#
# Organization       Model Name                Model String for API                    Default Steps
# --------------------------------------------------------------------------------------------------
# Black Forest Labs  Flux.1 [schnell] (free)*  black-forest-labs/FLUX.1-schnell-Free     N/A  (rate limit = 10 img/min)
# Black Forest Labs  Flux.1 [schnell] (Turbo)  black-forest-labs/FLUX.1-schnell            4
# Black Forest Labs  Flux.1 Dev                black-forest-labs/FLUX.1-dev               28
# Black Forest Labs  Flux.1 Canny              black-forest-labs/FLUX.1-canny             28
# Black Forest Labs  Flux.1 Depth              black-forest-labs/FLUX.1-depth             28
# Black Forest Labs  Flux.1 Redux              black-forest-labs/FLUX.1-redux             28
# Black Forest Labs  Flux1.1 [pro]             black-forest-labs/FLUX.1.1-pro              -
# Black Forest Labs  Flux.1 [pro]              black-forest-labs/FLUX.1-pro                -
# Stability AI       Stable Diffusion XL 1.0   stabilityai/stable-diffusion-xl-base-1.0    -
#


class TogetherImageGenerator(ImageGenerator):
    def check(self) -> None:
        assert settings.TOGETHER_API_KEY, "TOGETHER_API_KEY 환경변수 누락"

    async def make(self, query: str, width: int = 1024, height: int = 1024) -> PILImage:
        authorization = f"Bearer {settings.TOGETHER_API_KEY}"

        # TODO: 모델 등의 옵션 지원
        model = "black-forest-labs/FLUX.1-schnell-Free"
        steps: int = 4  # Number of generation steps. (default: 20)
        seed: int | None = None
        n: int | None = 1
        negative_prompt: str | None = None

        # https://docs.together.ai/docs/images-overview
        # https://docs.together.ai/reference/post_images-generations
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.together.xyz/v1/images/generations",
                headers={"Authorization": authorization, "Content-Type": "application/json"},
                json={
                    "prompt": query,
                    "model": model,
                    "steps": steps,
                    "seed": seed,
                    "n": n,
                    "height": height,
                    "width": width,
                    "negative_prompt": negative_prompt,
                },
            )
            obj = response.json()
            if "error" in obj:
                return "Error : " + obj["error"]["message"]

            image_url = obj["data"][0]["url"]
            return await fetch_image(image_url)
