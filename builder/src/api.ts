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

    protected get = async (url: string) => {
        return this.apiFetch(url, "GET");
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
    return `/api/experimental/${path.join("/")}/`;
};

class ApiUrls {
    static currentUser = () => apiUrl("current-user");
    static initiateUpload = () => apiUrl("usermedia", "initiate-upload");
    static createPartUploadUrls = (usermediaId: string) =>
        apiUrl("usermedia", usermediaId, "create-part-upload-urls");
    static finishUpload = (usermediaId: string) =>
        apiUrl("usermedia", usermediaId, "finish-upload");
    static abortUpload = (usermediaId: string) =>
        apiUrl("usermedia", usermediaId, "abort-upload");
    static submitPackage = () => apiUrl("package", "submit");
}

export interface UserMedia {
    uuid: string;
    datetime_created: string;
    expiry: string;
    status: string;
    filename: string;
    size: number;
}

interface UploadPartUrl {
    part_number: number;
    url: string;
}

interface UserMediaCreateUploadUrlsParams {
    file_size_bytes: number;
}

interface CreatePartUploadUrlsProps {
    usermediaId: string;
    data: UserMediaCreateUploadUrlsParams;
}

interface UserMediaUploadUrls {
    upload_urls: UploadPartUrl[];
    part_size: number;
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

class ExperimentalApiImpl extends ThunderstoreApi {
    currentUser = async () => {
        const response = await this.get(ApiUrls.currentUser());
        return await response.json();
    };

    initiateUpload = async (props: {
        data: { filename: string; file_size_bytes: number };
    }) => {
        const response = await this.post(ApiUrls.initiateUpload(), props.data);
        return (await response.json()) as UserMedia;
    };

    createPartUploadUrls = async (props: CreatePartUploadUrlsProps) => {
        const response = await this.post(
            ApiUrls.createPartUploadUrls(props.usermediaId),
            props.data
        );
        return (await response.json()) as UserMediaUploadUrls;
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
        return await response.json();
    };
}

export const ExperimentalApi = new ExperimentalApiImpl(getCookie("sessionid"));
