from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


GA_SCRIPT_TEMPLATE = """
<!-- Global site tag (gtag.js) - Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=%(ga_id)s"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', '%(ga_id)s');
</script>
"""


@register.simple_tag
def google_analytics():
    if settings.GOOGLE_ANALYTICS_ID:
        return mark_safe(GA_SCRIPT_TEMPLATE % {"ga_id": settings.GOOGLE_ANALYTICS_ID})
    else:
        return ""
