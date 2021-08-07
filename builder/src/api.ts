import { getCookie } from "./utils";

class ThunderstoreApi {
    apiKey: string | null;

    constructor(apiKey: string | null) {
        this.apiKey = apiKey;
    }

    protected apiFetch = async (
        url: string,
        method: "GET" | "POST",
        body?: string
    ) => {
        const headers = new Headers({
            "Content-Type": "application/json",
        });
        if (this.apiKey) {
            headers.set("Authorization", `Session ${this.apiKey}`);
        }
        const result = await fetch(url, {
            method: method,
            headers: headers,
            body: body,
        });
        if (result.status < 200 || result.status >= 300) {
            throw new Error(
                `Invalid HTTP response status: ${result.status} ${result.statusText}`
            );
        }
        return result;
    };

    protected get = async (url: string, data?: object) => {
        const queryUrl = new URL(url);
        if (data) {
            for (const [key, val] of Object.entries(data)) {
                queryUrl.searchParams.set(key, val);
            }
        }
        return this.apiFetch(queryUrl.toString(), "GET");
    };

    protected post = async (url: string, data?: object) => {
        return this.apiFetch(
            url,
            "POST",
            data ? JSON.stringify(data) : undefined
        );
    };
}

const apiUrl = (...path: string[]) => {
    const apiHost = window.location.origin;
    return `${apiHost}/api/experimental/${path.join("/")}/`;
};

class ApiUrls {
    static currentUser = () => apiUrl("current-user");
    static currentCommunity = () => apiUrl("current-community");
    static initiateUpload = () => apiUrl("usermedia", "initiate-upload");
    static finishUpload = (usermediaId: string) =>
        apiUrl("usermedia", usermediaId, "finish-upload");
    static abortUpload = (usermediaId: string) =>
        apiUrl("usermedia", usermediaId, "abort-upload");
    static submitPackage = () => apiUrl("submission", "submit");
    static listCommunities = () => apiUrl("community");
    static listCategories = (communityIdentifier: string) =>
        apiUrl("community", communityIdentifier, "category");
    static renderMarkdown = () => apiUrl("frontend", "render-markdown");
}

export interface UserMedia {
    uuid: string;
    datetime_created: string;
    expiry: string;
    status: string;
    filename: string;
    size: number;
}

export interface PackageVersion {
    date_created: string;
    dependencies: string[];
    description: string;
    download_url: string;
    downloads: number;
    full_name: string;
    icon: string;
    is_active: boolean;
    name: string;
    namespace: string;
    version_number: string;
    website_url: string;
}

export interface Community {
    identifier: string;
    name: string;
    discord_url: string;
    wiki_url: string;
    require_package_listing_approval: boolean;
}

export interface PaginatedResult<T> {
    pagination: {
        next_link: string | null;
        previous_link: string | null;
    };
    results: T[];
}

export interface UploadPartUrl {
    part_number: number;
    url: string;
    offset: number;
    length: number;
}

export interface UserMediaInitiateUploadResponse {
    user_media: UserMedia;
    upload_urls: UploadPartUrl[];
}

export interface CompletedPart {
    ETag: string;
    PartNumber: number;
}

interface UserMediaFinishUploadParams {
    parts: CompletedPart[];
}

interface FinishUploadProps {
    usermediaId: string;
    data: UserMediaFinishUploadParams;
}

interface RenderMarkdownResult {
    html: string;
}

interface CurrentUserInfo {
    username: string | null;
    capabilities: string[];
    ratedPackages: string[];
    teams: string[];
}

export interface PackageCategory {
    name: string;
    slug: string;
}

export interface PackageAvailableCommunity {
    community: Community;
    categories: PackageCategory[];
    url: string;
}

export interface PackageSubmissionResult {
    package_version: PackageVersion;
    available_communities: PackageAvailableCommunity[];
}

class ExperimentalApiImpl extends ThunderstoreApi {
    currentUser = async () => {
        const response = await this.get(ApiUrls.currentUser());
        return (await response.json()) as CurrentUserInfo;
    };

    currentCommunity = async () => {
        const response = await this.get(ApiUrls.currentCommunity());
        return (await response.json()) as Community;
    };

    initiateUpload = async (props: {
        data: { filename: string; file_size_bytes: number };
    }) => {
        const response = await this.post(ApiUrls.initiateUpload(), props.data);
        return (await response.json()) as UserMediaInitiateUploadResponse;
    };

    finishUpload = async (props: FinishUploadProps) => {
        const response = await this.post(
            ApiUrls.finishUpload(props.usermediaId),
            props.data
        );
        return (await response.json()) as UserMedia;
    };

    abortUpload = async (props: { usermediaId: string }) => {
        const response = await this.post(
            ApiUrls.abortUpload(props.usermediaId)
        );
        return (await response.json()) as UserMedia;
    };

    submitPackage = async (props: {
        data: {
            author_name: string;
            categories: string[];
            communities: string[];
            has_nsfw_content: boolean;
            upload_uuid: string;
        };
    }) => {
        const response = await this.post(ApiUrls.submitPackage(), props.data);
        return (await response.json()) as PackageSubmissionResult;
    };

    listCommunities = async (props?: { data?: { cursor?: string } }) => {
        const response = await this.get(ApiUrls.listCommunities(), props?.data);
        return (await response.json()) as PaginatedResult<Community>;
    };

    listCategories = async (props: {
        communityIdentifier: string;
        data?: { cursor?: string };
    }) => {
        const response = await this.get(
            ApiUrls.listCategories(props.communityIdentifier),
            props.data
        );
        return (await response.json()) as PaginatedResult<PackageCategory>;
    };

    renderMarkdown = async (props: { data: { markdown: string } }) => {
        const response = await this.post(ApiUrls.renderMarkdown(), props.data);
        return (await response.json()) as RenderMarkdownResult;
    };
}

export const ExperimentalApi = new ExperimentalApiImpl(getCookie("sessionid"));
