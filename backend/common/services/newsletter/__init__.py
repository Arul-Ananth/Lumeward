from backend.common.services.newsletter.pipeline import GenerationRequest, NewsletterPipeline, newsletter_pipeline
from backend.common.services.newsletter.templates import BUILTIN_TEMPLATES, NewsletterTemplateDefinition

__all__ = [
    "BUILTIN_TEMPLATES",
    "NewsletterPipeline",
    "GenerationRequest",
    "NewsletterTemplateDefinition",
    "newsletter_pipeline",
]
