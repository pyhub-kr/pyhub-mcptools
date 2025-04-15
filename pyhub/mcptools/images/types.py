from django.db.models.enums import TextChoices


class ImageGeneratorVendor(TextChoices):
    UNSPLASH = "UNSPLASH"
    TOGETHER_AI = "TOGETHER_AI"
    # TODO: DALLE
    # TODO: STABLE_DIFFUSION
    # TODO: Google Image Gen
