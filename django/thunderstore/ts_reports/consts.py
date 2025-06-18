REPORT_DESCRIPTION_MAX_LENGTH = 12288

REPORT_REASON_CHOICES = [
    {"value": "Spam", "label": "Spam"},
    {"value": "Malware", "label": "Suspected malware"},
    {"value": "Reupload", "label": "Unauthorized reupload"},
    {
        "value": "CopyrightOrLicense",
        "label": "Copyright / License issue",
    },
    {"value": "WrongCommunity", "label": "Wrong community"},
    {"value": "WrongCategories", "label": "Wrong categories"},
    {"value": "Other", "label": "Other"},
]
REPORT_REASON_CHOICES_TUPLES = [(x["value"], x["label"]) for x in REPORT_REASON_CHOICES]
