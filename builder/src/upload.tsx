import React, { CSSProperties, useEffect, useRef, useState } from "react";
import { CompletedPart, ExperimentalApi } from "./api";
import * as crypto from "crypto-js";

interface UploadFileInputProps {
    title: string;
    onChange?: (files: FileList) => void;
    readonly?: boolean;
}

export const UploadFileInput: React.FC<UploadFileInputProps> = (props) => {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [fileDropStyle, setFileDropStyle] = useState<CSSProperties>({});
    const [lastTarget, setLastTarget] = useState<EventTarget | null>(null);
    const [isDragging, setIsDragging] = useState<boolean>(false);

    const resetDragState = () => {
        setIsDragging(false);
        setFileDropStyle({
            height: undefined,
            border: undefined,
        });
    };
    const windowDragEnter = (e: DragEvent) => {
        setIsDragging(true);
        setLastTarget(e.target);
        if (!props.readonly) {
            setFileDropStyle({
                height: "200px",
                border: "4px solid #fff",
            });
        }
    };
    const windowDragLeave = (e: DragEvent) => {
        if (e.target === lastTarget || e.target === document) {
            resetDragState();
        }
    };
    const windowDrop = () => {
        resetDragState();
    };
    const fileChange = () => {
        resetDragState();
    };
    const onDrop = (e: React.DragEvent) => {
        if (!props.readonly) {
            const inp = fileInputRef.current;
            if (inp) {
                inp.files = e.dataTransfer.files;
            }
            if (props.onChange) {
                props.onChange(e.dataTransfer.files);
            }
        }
        e.preventDefault();
        resetDragState();
    };

    useEffect(() => {
        window.addEventListener("dragenter", windowDragEnter);
        window.addEventListener("dragleave", windowDragLeave);
        window.addEventListener("drop", windowDrop);
        return () => {
            window.removeEventListener("dragenter", windowDragEnter);
            window.removeEventListener("dragleave", windowDragLeave);
            window.removeEventListener("drop", windowDrop);
        };
    });

    const extraClass = !!props.readonly ? "disabled" : "";
    const finalStyle = {
        height: fileDropStyle.height,
        border: fileDropStyle.border,
        cursor: !!props.readonly ? undefined : "pointer",
    };

    return (
        <label
            className={`btn btn-primary btn-lg btn-block ${extraClass}`}
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop}
            style={finalStyle}
            aria-disabled={props.readonly}
        >
            {isDragging && !props.readonly ? "Drag file here" : props.title}
            <input
                type="file"
                name="newfile"
                style={{ display: "none" }}
                ref={fileInputRef}
                onChange={fileChange}
                disabled={props.readonly}
            />
        </label>
    );
};

const calculateMD5 = (blob: Blob) => {
    return new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.readAsBinaryString(blob);
        reader.onloadend = () => {
            const md5 = crypto.MD5(
                crypto.enc.Latin1.parse(reader.result!.toString())
            );
            resolve(md5.toString(crypto.enc.Base64));
        };
    });
};

export const UploadForm: React.FC = () => {
    const [file, setFile] = useState<File | null>(null);
    const [progress, setProgress] = useState<number | null>(null);
    const [uploadComplete, setUploadComplete] = useState<boolean>(false);
    const [uploadError, setUploadError] = useState<boolean>(false);
    const [uploadUuid, setUploadUuid] = useState<string | null>(null);
    const uploadCanceled = useRef<boolean>(false);

    const onFileChange = (files: FileList) => {
        setFile(files.item(0));
        setUploadUuid(null);
    };

    const beginUpload = async (file: File | null) => {
        if (!file) return;
        if (!!uploadUuid) return;
        setUploadComplete(false);
        setUploadError(false);
        setProgress(null);
        uploadCanceled.current = false;
        const handle = await ExperimentalApi.initiateUpload({
            data: {
                filename: file.name,
                file_size_bytes: file.size,
            },
        });
        setUploadUuid(handle.uuid);
        const urls = await ExperimentalApi.createPartUploadUrls({
            usermediaId: handle.uuid,
            data: { file_size_bytes: file.size },
        });
        const totalParts = urls.upload_urls.length;
        setProgress(0);
        const partSize = urls.part_size;
        const completedParts: CompletedPart[] = [];
        const uploadPromises = [];
        for (const partInfo of urls.upload_urls) {
            const partIndex = partInfo.part_number - 1;
            const start = partIndex * partSize;
            const end = (partIndex + 1) * partSize;
            const blob =
                end < file.size ? file.slice(start, end) : file.slice(start);
            const promise = calculateMD5(blob)
                .then((md5) => {
                    if (uploadCanceled.current) {
                        throw new Error("Upload was aborted by the user");
                    }
                    return fetch(partInfo.url, {
                        method: "PUT",
                        headers: new Headers({
                            "Content-Length": `${blob.size}`,
                            "Content-MD5": md5,
                        }),
                        body: blob,
                    });
                })
                .then((completionInfo) => {
                    if (completionInfo.ok) {
                        completedParts.push({
                            ETag: completionInfo.headers.get("ETag")!,
                            PartNumber: partInfo.part_number,
                        });
                    } else {
                        setProgress(100);
                        setUploadError(true);
                        throw new Error(
                            `Failed part upload: ${completionInfo.statusText}`
                        );
                    }
                    if (!uploadCanceled.current) {
                        setProgress(completedParts.length / totalParts);
                    }
                });
            uploadPromises.push(promise);
        }
        await Promise.all(uploadPromises);
        if (!uploadCanceled.current) {
            await ExperimentalApi.finishUpload({
                usermediaId: handle.uuid,
                data: {
                    parts: completedParts,
                },
            });
            setUploadUuid(handle.uuid);
            setUploadComplete(true);
        }
    };

    const cancel = async () => {
        uploadCanceled.current = true;
        setFile(null);
        if (uploadUuid && !uploadComplete) {
            try {
                await ExperimentalApi.abortUpload({ usermediaId: uploadUuid });
            } catch {}
        }
        setUploadComplete(false);
        setUploadError(false);
        setProgress(null);
        setUploadUuid(null);
    };

    const submit = async () => {
        if (!uploadUuid) return;
        try {
            await ExperimentalApi.submitPackage({
                data: {
                    // TODO: Read from the form
                    upload_uuid: uploadUuid,
                    author_name: "uploadtest",
                    categories: [],
                    communities: ["riskofrain2"],
                    has_nsfw_content: false,
                },
            });
        } catch (e) {
            console.log(e);
        }
    };

    const progressBg = uploadError
        ? "bg-danger"
        : uploadComplete
        ? "bg-success"
        : "";

    return (
        <div>
            <UploadFileInput
                title={file ? file.name : "Choose or drag file here"}
                onChange={onFileChange}
                readonly={!!file}
            />
            {progress !== null && (
                <div className="progress mb-2">
                    <div
                        className={`progress-bar progress-bar-striped progress-bar-animated ${progressBg}`}
                        role="progressbar"
                        aria-valuenow={Math.trunc(progress * 100)}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        style={{ width: `${Math.trunc(progress * 100)}%` }}
                    />
                </div>
            )}
            <button
                disabled={!file || !!uploadUuid}
                onClick={() => beginUpload(file)}
                className="btn btn-success btn-block"
            >
                Upload
            </button>
            <button
                disabled={!file}
                onClick={cancel}
                className="btn btn-danger btn-block"
            >
                Cancel
            </button>
            <button
                disabled={!(uploadUuid && uploadComplete)}
                onClick={submit}
                className="btn btn-primary btn-block"
            >
                Submit
            </button>
        </div>
    );
};
