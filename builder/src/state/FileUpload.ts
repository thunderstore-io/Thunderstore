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
    UploadPartUrl,
    UserMediaInitiateUploadResponse,
} from "../api";
import { calculateMD5 } from "../utils";

export enum FileUploadStatus {
    NEW = "NEW",
    INITIATING = "INITIATING",
    UPLOADING = "UPLOADING",
    COMPLETE = "COMPLETE",
    ERRORED = "ERRORED",
    CANCELED = "CANCELED",
}

export class FileUpload {
    @observable uploadStatus: FileUploadStatus = FileUploadStatus.NEW;
    @observable private _maxProgress: number | null = null;
    @observable private _currentProgress: number | null = null;
    @observable
    private _uploadInfo: UserMediaInitiateUploadResponse | null = null;

    constructor() {
        makeObservable(this);
    }

    @action
    resetState = () => {
        this.uploadStatus = FileUploadStatus.NEW;
        this._maxProgress = null;
        this._currentProgress = null;
    };

    @action
    private setUploadStatus(status: FileUploadStatus) {
        if (this.uploadStatus != FileUploadStatus.CANCELED) {
            this.uploadStatus = status;
        }
    }

    @action
    private startProgress(maxProgress: number) {
        if (this.uploadStatus != FileUploadStatus.CANCELED) {
            this._maxProgress = maxProgress;
            this._currentProgress = 0;
        }
    }

    @action
    private adjustProgress(delta: number) {
        if (this.uploadStatus != FileUploadStatus.CANCELED) {
            if (this._currentProgress) {
                this._currentProgress += delta;
            } else {
                this._currentProgress = delta;
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
                if (this._maxProgress && this._currentProgress) {
                    return this._currentProgress / this._maxProgress;
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

    async uploadPart(
        file: File,
        partInfo: UploadPartUrl
    ): Promise<CompletedPart> {
        const start = partInfo.offset;
        const end = partInfo.offset + partInfo.length;
        const blob =
            end < file.size ? file.slice(start, end) : file.slice(start);

        const md5 = await this.cancelGuard(() => calculateMD5(blob));
        const completionInfo = await this.cancelGuard(() => {
            return fetch(partInfo.url, {
                method: "PUT",
                headers: new Headers({
                    "Content-Length": `${blob.size}`,
                    "Content-MD5": md5,
                }),
                body: blob,
            });
        });

        if (!completionInfo.ok) {
            this.setUploadStatus(FileUploadStatus.ERRORED);
            throw new Error(`Failed part upload: ${completionInfo.statusText}`);
        }

        this.adjustProgress(+1);
        return {
            ETag: completionInfo.headers.get("ETag")!,
            PartNumber: partInfo.part_number,
        };
    }

    public async cancelUpload() {
        const oldStatus = this.uploadStatus;
        this.setUploadStatus(FileUploadStatus.CANCELED);
        if (this._uploadInfo && oldStatus != FileUploadStatus.COMPLETE) {
            try {
                await ExperimentalApi.abortUpload({
                    usermediaId: this._uploadInfo.user_media.uuid,
                });
            } catch (e) {
                // TODO: Capture to Sentry
                console.log(e, e.stack);
            }
        }
    }

    public async upload(file: File): Promise<string | null> {
        if (this.uploadStatus != FileUploadStatus.NEW) return null;

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
            // TODO: Capture to Sentry
            console.error(e, e.stack);
            return null;
        }

        const uploadPromises = [];
        for (const partInfo of uploadInfo.upload_urls) {
            uploadPromises.push(this.uploadPart(file, partInfo));
        }

        let completedParts;
        try {
            completedParts = await Promise.all(uploadPromises);
        } catch (e) {
            this.setUploadStatus(FileUploadStatus.ERRORED);
            // TODO: Capture to Sentry
            console.error(e, e.stack);
            return null;
        }

        try {
            await this.finishUpload(uploadInfo, completedParts);
        } catch (e) {
            this.setUploadStatus(FileUploadStatus.ERRORED);
            // TODO: Capture to Sentry
            console.error(e, e.stack);
            return null;
        }
        return uploadInfo.user_media.uuid;
    }

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
            this.startProgress(uploadInfo.upload_urls.length);
            this.setUploadStatus(FileUploadStatus.UPLOADING);
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

        await ExperimentalApi.finishUpload({
            usermediaId: uploadInfo.user_media.uuid,
            data: {
                parts: completedParts,
            },
        });
        this.setUploadStatus(FileUploadStatus.COMPLETE);
    }
}
