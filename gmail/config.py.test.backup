class GmailConfig:
    """Configuration for Gmail service with sender filters and API settings."""

    def __init__(self) -> None:
        """Initialize Gmail configuration with preferred senders and limits."""
        self.preferred_senders = [
            "jenbarreda@yahoo.com",
            "518stoneman@gmail.com",
            "brad_martinez@att.net",
            "vicki_martinez@att.net",
            "dteshale@teshalelaw.com",
            "info@dignitylawgroup.com",
            "joe@kellenerlaw.com",
            "sally@lotuspropertyservices.net",
            "grace@lotuspropertyservices.net",
            "gaildcalhoun@gmail.com",
        ]
        self.max_results = 500  # Gmail API max per request

    def build_query(self) -> str:
        """Build Gmail API query string from configured sender filters.

        Returns:
            str: Gmail query string with OR-joined sender filters.
        """
        # Build sender filter only - no date restrictions
        sender_queries = [f"from:{sender}" for sender in self.preferred_senders]
        sender_filter = " OR ".join(sender_queries)

        # Return just the sender filter
        return f"({sender_filter})"
