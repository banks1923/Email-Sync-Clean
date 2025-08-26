class GmailConfig:
    """
    Configuration for Gmail service with sender filters and API settings.
    """

    def __init__(self) -> None:
        """
        Initialize Gmail configuration with preferred senders and limits.
        """
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

        # Dates to exclude from sync (format: YYYY/MM/DD)
        self.excluded_dates = [
            "2023/10/03",  # October 3rd, 2023
            "2023/12/18",  # December 18th, 2023
        ]

    def build_query(self) -> str:
        """Build Gmail API query string from configured sender filters.

        Returns:
            str: Gmail query string with OR-joined sender filters and date restriction.
        """
        # Build sender filter
        sender_queries = [f"from:{sender}" for sender in self.preferred_senders]
        sender_filter = " OR ".join(sender_queries)

        # Add date restriction to exclude emails before 2023
        date_filter = "after:2022/12/31"

        # Add exclusions for specific dates
        for excluded_date in self.excluded_dates:
            # Gmail doesn't support direct date exclusion, so we use before/after
            # We'll handle this in the processing stage instead
            pass

        # Return sender filter with date restriction
        # Note: Specific date exclusions will be handled during processing
        return f"({sender_filter}) {date_filter}"
