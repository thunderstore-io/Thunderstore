export type ReviewStatus = "unreviewed" | "approved" | "rejected";

export type JSONValue =
    | string
    | number
    | boolean
    | null
    | JSONValue[]
    | { [key: string]: JSONValue };

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

export interface FinishUploadProps {
    usermediaId: string;
    data: UserMediaFinishUploadParams;
}

export interface RenderMarkdownResult {
    html: string;
}

export interface CurrentUserInfo {
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

export interface PackageSubmissionData {
    author_name: string;
    community_categories: { [key: string]: string[] };
    communities: string[];
    has_nsfw_content: boolean;
    upload_uuid: string;
}

export interface SubmissionError {
    upload_uuid?: string[];
    author_name?: string[];
    categories?: string[];
    communities?: string[];
    has_nsfw_content?: string[];
    detail?: string;
    file?: string[];
    team?: string[];
    __all__?: string[];
}

export interface PackageSubmissionResult {
    package_version: PackageVersion;
    available_communities: PackageAvailableCommunity[];
}

export interface PackageAsyncSubmissionStatus {
    id: string;
    status: "PENDING" | "FINISHED";
    form_errors?: JSONValue;
    task_error: boolean;
    result?: PackageSubmissionResult;
}

export interface UpdatePackageListingResponse {
    categories: PackageCategory[];
}

export interface WikiPageUpsertRequest {
    id?: string | number;
    title: string;
    markdown_content: string;
}

export interface GenericApiError {
    detail?: string;
}

export interface BaseValidationError {
    non_field_errors?: string[];
    __all__?: string[];
}

export interface WikiDeleteError extends BaseValidationError {
    pageId?: string[];
}

export interface WikiPageUpsertError extends BaseValidationError {
    title?: string[];
    markdown_content?: string[];
}

export interface WikiPage {
    id: string;
    title: string;
    slug: string;
    datetime_created: string;
    datetime_updated: string;
    markdown_content: string;
}
