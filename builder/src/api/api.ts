import { getCookie } from "../utils";
import {
    Community,
    CurrentUserInfo,
    FinishUploadProps,
    PackageAsyncSubmissionStatus,
    PackageCategory,
    PackageSubmissionData,
    PackageSubmissionResult,
    PaginatedResult,
    RenderMarkdownResult,
    UpdatePackageListingResponse,
    UserMedia,
    UserMediaInitiateUploadResponse,
    WikiPage,
    WikiPageUpsertRequest,
} from "./models";
import { ApiUrls } from "./urls";
import { ThunderstoreApi } from "./client";

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

    submitPackage = async (props: { data: PackageSubmissionData }) => {
        const response = await this.post(ApiUrls.submitPackage(), props.data);
        return (await response.json()) as PackageSubmissionResult;
    };

    submitPackageAsync = async (props: { data: PackageSubmissionData }) => {
        const response = await this.post(
            ApiUrls.submitPackageAsync(),
            props.data
        );
        return (await response.json()) as PackageAsyncSubmissionStatus;
    };

    pollAsyncSubmission = async (props: { submissionId: string }) => {
        const response = await this.get(
            ApiUrls.pollAsyncSubmission(props.submissionId)
        );
        return (await response.json()) as PackageAsyncSubmissionStatus;
    };

    updatePackageListing = async (props: {
        packageListingId: string;
        data: {
            categories: string[];
        };
    }) => {
        const response = await this.post(
            ApiUrls.updatePackageListing(props.packageListingId),
            props.data
        );
        return (await response.json()) as UpdatePackageListingResponse;
    };

    approvePackageListing = async (props: { packageListingId: string }) => {
        await this.post(ApiUrls.approvePackageListing(props.packageListingId));
    };

    rejectPackageListing = async (props: {
        packageListingId: string;
        data: {
            rejection_reason: string;
        };
    }) => {
        await this.post(
            ApiUrls.rejectPackageListing(props.packageListingId),
            props.data
        );
    };

    listCommunities = async () => {
        const response = await this.get(ApiUrls.listCommunities());
        return (await response.json()) as PaginatedResult<Community>;
    };

    listCategories = async (props: { communityIdentifier: string }) => {
        const response = await this.get(
            ApiUrls.listCategories(props.communityIdentifier)
        );
        return (await response.json()) as PaginatedResult<PackageCategory>;
    };

    getNextPage = async <T>(cursor: string) => {
        const response = await this.get(cursor);
        return (await response.json()) as PaginatedResult<T>;
    };

    renderMarkdown = async (props: { data: { markdown: string } }) => {
        const response = await this.post(ApiUrls.renderMarkdown(), props.data);
        return (await response.json()) as RenderMarkdownResult;
    };

    validateManifestV1 = async (props: {
        data: { namespace: string; manifest_data: string };
    }) => {
        const response = await this.post(
            ApiUrls.validateManifestV1(),
            props.data
        );
        return (await response.json()) as { success: boolean };
    };

    upsertPackageWikiPage = async (props: {
        namespace: string;
        name: string;
        data: WikiPageUpsertRequest;
    }) => {
        const response = await this.post(
            ApiUrls.packageWiki(props.namespace, props.name),
            props.data
        );
        return (await response.json()) as WikiPage;
    };

    deletePackageWikiPage = async (props: {
        namespace: string;
        name: string;
        pageId: string;
    }) => {
        const response = await this.delete(
            ApiUrls.packageWiki(props.namespace, props.name),
            { id: props.pageId }
        );
        return (await response.json()) as { success: boolean };
    };
}

export const ExperimentalApi = new ExperimentalApiImpl(getCookie("sessionid"));
