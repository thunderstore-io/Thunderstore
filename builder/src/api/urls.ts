export const apiUrl = (...path: string[]) => {
    const apiHost = window.location.origin;
    return `${apiHost}/api/experimental/${path.join("/")}/`;
};

export class ApiUrls {
    static currentUser = () => apiUrl("current-user");
    static currentCommunity = () => apiUrl("current-community");
    static initiateUpload = () => apiUrl("usermedia", "initiate-upload");
    static finishUpload = (usermediaId: string) =>
        apiUrl("usermedia", usermediaId, "finish-upload");
    static abortUpload = (usermediaId: string) =>
        apiUrl("usermedia", usermediaId, "abort-upload");
    static submitPackage = () => apiUrl("submission", "submit");
    static submitPackageAsync = () => apiUrl("submission", "submit-async");
    static pollAsyncSubmission = (submissionId: string) =>
        apiUrl("submission", "poll-async", submissionId);
    static listCommunities = () => apiUrl("community");
    static listCategories = (communityIdentifier: string) =>
        apiUrl("community", communityIdentifier, "category");
    static renderMarkdown = () => apiUrl("frontend", "render-markdown");
    static validateManifestV1 = () =>
        apiUrl("submission", "validate", "manifest-v1");
    static updatePackageListing = (packageListingId: string) =>
        apiUrl("package-listing", packageListingId, "update");
    static reportPackageListing = (packageListingId: string) =>
        apiUrl("package-listing", packageListingId, "report");
    static approvePackageListing = (packageListingId: string) =>
        apiUrl("package-listing", packageListingId, "approve");
    static rejectPackageListing = (packageListingId: string) =>
        apiUrl("package-listing", packageListingId, "reject");
    static packageWiki = (namespace: string, name: string) =>
        apiUrl("package", namespace, name, "wiki");
}
