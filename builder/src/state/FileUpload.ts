import * as Sentry from "@sentry/react";
import {
    action,
    computed,
    makeObservable,
    observable,
    transaction,
} from "mobx";
import {
    CompletedPart,
    ExperimentalApi,
    stringifyError,
    ThunderstoreApiError,
    UploadPartUrl,
    UserMediaInitiateUploadResponse,
} from "../api";
import { calculateMD5, fetchWithProgress } from "../utils";
import { WorkerManager, Workers } from "../workers";
import { PromiseThrottler } from "../throttle";
import { retry } from "../retry";

export enum FileUploadStatus {
    NEW = "NEW",
    INITIATING = "INITIATING",
    UPLOADING = "UPLOADING",
    COMPLETE = "COMPLETE",
    ERRORED = "ERRORED",
    CANCELED = "CANCELED",
}

const MAX_UPLOAD_ATTEMPTS = 10;
const MAX_PARALLEL_REQUESTS = 3;

export class FileUpload {
    @observable uploadErrors: string[] = [];
    @observable uploadStatus: FileUploadStatus = FileUploadStatus.NEW;
    @observable private _progress: Map<number, number> | null = null;
    @observable
    private _uploadInfo: UserMediaInitiateUploadResponse | null = null;

    private _ongoingRequests: Set<XMLHttpRequest> | null = null;

    private throttler: PromiseThrottler = new PromiseThrottler(
        MAX_PARALLEL_REQUESTS
    );

    constructor() {
        makeObservable(this);
    }

    @action
    resetState = () => {
        this.uploadStatus = FileUploadStatus.NEW;
        this.uploadErrors = [];
        this._progress = null;
    };

    @action
    private setUploadStatus(status: FileUploadStatus) {
        if (this.uploadStatus != FileUploadStatus.CANCELED) {
            this.uploadStatus = status;
        }
    }

    @action
    private logErrors(...errors: string[]) {
        if (!errors || errors.length == 0) return;
        this.uploadErrors.push(...errors);
        console.error(errors);
    }

    @action
    private logApiError(error: unknown | Error | ThunderstoreApiError) {
        if (error instanceof ThunderstoreApiError) {
            const flattened = stringifyError(error.errorObject);
            this.logErrors(...flattened);
        } else if (error instanceof Error) {
            this.logErrors(error.message || "Unknown error");
            console.error(error, error.stack);
        } else {
            this.logErrors(`${error}` || "Unknown error");
            console.error(error);
        }
    }

    @action
    private startProgress(info: UserMediaInitiateUploadResponse) {
        if (this.uploadStatus != FileUploadStatus.CANCELED) {
            this._progress = new Map<number, number>(
                info.upload_urls.map((val) => [val.part_number, 0])
            );
        }
    }

    @action
    private setProgress(partNumber: number, progress: number) {
        if (this.uploadStatus != FileUploadStatus.CANCELED) {
            if (this._progress != null) {
                this._progress.set(partNumber, progress);
            } else {
                this._progress = new Map<number, number>([
                    [partNumber, progress],
                ]);
            }
        }
    }

    @computed
    get uploadProgress(): number | null {
        switch (this.uploadStatus) {
            case FileUploadStatus.COMPLETE:
                return 100;
            case FileUploadStatus.CANCELED:
                return 100;
            case FileUploadStatus.ERRORED:
                return 100;
            case FileUploadStatus.NEW:
                return null;
            case FileUploadStatus.INITIATING:
                return 0;
            case FileUploadStatus.UPLOADING:
                if (this._progress != null && this._progress.size > 0) {
                    let total = 0;
                    for (const entry of this._progress.values()) {
                        total += entry;
                    }
                    return total / this._progress.size;
                } else {
                    return 0;
                }
        }
    }

    // All awaits during which the upload might be cancelled should be wrapped
    // with this
    async cancelGuard<T>(fn: () => Promise<T>): Promise<T> {
        if (
            (this.uploadStatus as FileUploadStatus) == FileUploadStatus.CANCELED
        ) {
            throw new Error("Upload was aborted by the user");
        }
        const result = await fn();
        if (
            (this.uploadStatus as FileUploadStatus) == FileUploadStatus.CANCELED
        ) {
            throw new Error("Upload was aborted by the user");
        }
        return result;
    }

    async _uploadPart(
        file: File,
        partInfo: UploadPartUrl
    ): Promise<CompletedPart> {
        const start = partInfo.offset;
        const end = partInfo.offset + partInfo.length;
        const blob =
            end < file.size ? file.slice(start, end) : file.slice(start);

        const md5 = await this.cancelGuard(() => {
            if (window.Worker) {
                return WorkerManager.callWorker<string>(Workers.MD5, blob);
            } else {
                return calculateMD5(blob);
            }
        });

        let completionInfo: Response;
        try {
            completionInfo = await this.cancelGuard(() => {
                const { request, response } = fetchWithProgress(
                    partInfo.url,
                    {
                        method: "PUT",
                        headers: new Headers({
                            "Content-MD5": md5,
                        }),
                        body: blob,
                    },
                    (event) => {
                        this.setProgress(
                            partInfo.part_number,
                            event.loaded / event.total
                        );
                    }
                );
                if (!this._ongoingRequests) {
                    this._ongoingRequests = new Set();
                }
                this._ongoingRequests.add(request);
                return response.then((resp) => {
                    if (this._ongoingRequests) {
                        this._ongoingRequests.delete(request);
                    }
                    return resp;
                });
            });
        } catch (e: any) {
            if (this.uploadStatus != FileUploadStatus.ERRORED) {
                this.uploadErrors.push(
                    "A browser plugin or anti-virus software may be blocking connection to the server."
                );
            }
            this.setUploadStatus(FileUploadStatus.ERRORED);
            const shortUrl = partInfo.url.substring(
                0,
                partInfo.url.lastIndexOf("/") + 1
            );
            throw new Error(
                `Network error uploading part ${
                    partInfo.part_number
                } to ${shortUrl}: ${e?.message || e}`
            );
        }

        if (!completionInfo.ok) {
            this.setUploadStatus(FileUploadStatus.ERRORED);
            throw new Error(`Failed part upload: ${completionInfo.statusText}`);
        }

        this.setProgress(partInfo.part_number, 1);
        return {
            ETag: completionInfo.headers.get("etag")!,
            PartNumber: partInfo.part_number,
        };
    }

    async uploadPart(
        file: File,
        partInfo: UploadPartUrl
    ): Promise<CompletedPart> {
        return await this.throttler.throttle(() =>
            this.cancelGuard(() =>
                retry(
                    MAX_UPLOAD_ATTEMPTS,
                    () =>
                        this.cancelGuard(() =>
                            this._uploadPart(file, partInfo)
                        ),
                    () => this.uploadStatus !== FileUploadStatus.CANCELED,
                    (e) => this.logApiError(e)
                )
            )
        );
    }

    public async cancelUpload() {
        const oldStatus = this.uploadStatus;
        this.setUploadStatus(FileUploadStatus.CANCELED);
        if (this._ongoingRequests) {
            for (const request of this._ongoingRequests.values()) {
                try {
                    request.abort();
                } catch (e) {
                    Sentry.captureException(e);
                    console.error(e);
                }
            }
            this._ongoingRequests = null;
        }
        if (this._uploadInfo && oldStatus != FileUploadStatus.COMPLETE) {
            try {
                await ExperimentalApi.abortUpload({
                    usermediaId: this._uploadInfo.user_media.uuid,
                });
            } catch (e) {
                Sentry.captureException(e);
                console.error(e);
            }
        }
    }

    public async upload(file: File): Promise<string | null> {
        if (this.uploadStatus != FileUploadStatus.NEW) return null;
        if (file.size <= 0) {
            this.setUploadStatus(FileUploadStatus.ERRORED);
            this.logErrors("Attempted to upload a file with 0 size");
            return null;
        }

        transaction(() => {
            this.resetState();
            this.setUploadStatus(FileUploadStatus.INITIATING);
        });

        let uploadInfo;
        try {
            uploadInfo = await this.cancelGuard(() =>
                this.initiateUpload(file)
            );
        } catch (e) {
            this.setUploadStatus(FileUploadStatus.ERRORED);
            Sentry.captureException(e);
            this.logApiError(e);
            return null;
        }

        const uploadPromises = [];
        for (const partInfo of uploadInfo.upload_urls) {
            this._ongoingRequests = new Set();
            uploadPromises.push(this.uploadPart(file, partInfo));
        }

        let completedParts;
        try {
            completedParts = await Promise.all(uploadPromises);
        } catch (e) {
            this.setUploadStatus(FileUploadStatus.ERRORED);
            Sentry.captureException(e);
            this.logApiError(e);
            return null;
        }

        try {
            await this.finishUpload(uploadInfo, completedParts);
        } catch (e) {
            this.setUploadStatus(FileUploadStatus.ERRORED);
            Sentry.captureException(e);
            this.logApiError(e);
            return null;
        }
        return uploadInfo.user_media.uuid;
    }

    @action
    private async initiateUpload(
        file: File
    ): Promise<UserMediaInitiateUploadResponse> {
        const status = this.uploadStatus;
        if (status != FileUploadStatus.INITIATING) {
            throw new Error(
                `Unable to initiate upload; upload in invalid state: ${status}`
            );
        }

        const uploadInfo = await this.cancelGuard(() =>
            ExperimentalApi.initiateUpload({
                data: {
                    filename: file.name,
                    file_size_bytes: file.size,
                },
            })
        );
        transaction(() => {
            this.startProgress(uploadInfo);
            this.setUploadStatus(FileUploadStatus.UPLOADING);
            this._uploadInfo = uploadInfo;
        });
        return uploadInfo;
    }

    private async finishUpload(
        uploadInfo: UserMediaInitiateUploadResponse,
        completedParts: CompletedPart[]
    ) {
        const status = this.uploadStatus;

        if (status != FileUploadStatus.UPLOADING) {
            throw new Error(
                `Unable to finalize upload; upload in invalid state: ${status}`
            );
        }
        if (!uploadInfo || uploadInfo.upload_urls.length == 0) {
            throw new Error(`Unable to finalize upload; no upload tracked`);
        }
        if (
            !completedParts ||
            completedParts.length < uploadInfo.upload_urls.length
        ) {
            throw new Error(
                `Unable to finalize upload; not all parts have been uploaded`
            );
        }

        await retry(
            MAX_UPLOAD_ATTEMPTS,
            () =>
                ExperimentalApi.finishUpload({
                    usermediaId: uploadInfo.user_media.uuid,
                    data: {
                        parts: completedParts,
                    },
                }),
            () => true,
            (e) => this.logApiError(e)
        );
        this.setUploadStatus(FileUploadStatus.COMPLETE);
    }
}
