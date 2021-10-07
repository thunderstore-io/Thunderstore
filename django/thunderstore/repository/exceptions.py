class RedirectListingException(Exception):
    def __init__(self, listing):
        self.listing = listing
        super().__init__("Listing found in another community")
