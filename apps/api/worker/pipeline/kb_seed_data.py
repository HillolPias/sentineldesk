"""
Fictional support knowledge base for SentinelDesk's demo tenant(s).
In a real product this would come from actual docs/help-center content;
here it's deliberately small and plausible so RAG has something real to retrieve.
"""

KB_ARTICLES = [
    {
        "id": "kb-001",
        "title": "Resetting your password",
        "content": (
            "To reset your password, go to Settings > Account > Security and click "
            "'Reset Password'. A reset link is sent to your registered email and expires "
            "after 30 minutes. If you don't receive the email, check your spam folder "
            "before contacting support."
        ),
        "category": "account",
    },
    {
        "id": "kb-002",
        "title": "Billing cycle and invoices",
        "content": (
            "Invoices are generated on the 1st of each month based on your plan's usage "
            "in the prior billing cycle. You can view past invoices under Settings > "
            "Billing > Invoice History. Refunds for billing errors are processed within "
            "5-7 business days."
        ),
        "category": "billing",
    },
    {
        "id": "kb-003",
        "title": "API rate limits",
        "content": (
            "Free tier accounts are limited to 100 API requests per minute per tenant. "
            "Exceeding this returns a 429 status code. Rate limits reset every 60 seconds. "
            "Upgrading to a paid plan raises the limit to 1000 requests per minute."
        ),
        "category": "technical",
    },
    {
        "id": "kb-004",
        "title": "Exporting your data",
        "content": (
            "You can export all account data as a CSV from Settings > Data > Export. "
            "Exports are generated asynchronously and emailed to you as a download link "
            "within 10 minutes, valid for 24 hours."
        ),
        "category": "account",
    },
    {
        "id": "kb-005",
        "title": "Cancelling a subscription",
        "content": (
            "Subscriptions can be cancelled anytime from Settings > Billing > Cancel Plan. "
            "Cancellation takes effect at the end of the current billing period; you retain "
            "access until then. No partial-month refunds are issued."
        ),
        "category": "billing",
    },
    {
        "id": "kb-006",
        "title": "Two-factor authentication setup",
        "content": (
            "Enable 2FA under Settings > Account > Security > Two-Factor Authentication. "
            "We support authenticator apps (TOTP) only; SMS-based 2FA is not currently "
            "available. Backup codes are shown once during setup — save them securely."
        ),
        "category": "account",
    },
]
