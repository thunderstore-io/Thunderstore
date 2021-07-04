import React, { useEffect, useState } from "react";
import { Community, ExperimentalApi } from "./api";
import { useForm } from "react-hook-form";
import { DragDropFileInput } from "./components/DragDropFileInput";
import { PackageSubmission } from "./state/PackageSubmission";
import { FileUpload, FileUploadStatus } from "./state/FileUpload";
import { observer } from "mobx-react";

function getProgressBarColor(uploadStatus: FileUploadStatus | undefined) {
    if (uploadStatus) {
        if (uploadStatus == FileUploadStatus.CANCELED) {
            return "bg-warning";
        } else if (uploadStatus == FileUploadStatus.ERRORED) {
            return "bg-danger";
        } else if (uploadStatus == FileUploadStatus.COMPLETE) {
            return "bg-success";
        }
    }
    return "bg-info";
}

interface UploadHandlerProps {
    onComplete: (uploadId: string | null) => void;
    className?: string;
}
const UploadHandler: React.FC<UploadHandlerProps> = observer(
    ({ onComplete, className }) => {
        const [file, setFile] = useState<File | null>(null);
        const [fileUpload, setFileUpload] = useState<FileUpload | null>(null);

        useEffect(() => {
            if (file) {
                // TODO: Add some global-state aware system which knows if
                //       other components are interested in managing
                //       onbeforeunload too, instead of simply overriding it
                window.onbeforeunload = () => {
                    return "You have a package submission in progress, are you sure you want to exit?";
                };
                return () => {
                    window.onbeforeunload = null;
                };
            } else {
                return () => {};
            }
        }, [file]);

        const onFileChange = (files: FileList) => {
            setFile(files.item(0));
        };

        const cancel = async () => {
            setFile(null);
            onComplete(null);
            if (fileUpload) {
                await fileUpload.cancelUpload();
            }
            setFileUpload(null);
        };

        const upload = async (file: File | null) => {
            if (!file) return;
            const upload = new FileUpload();
            setFileUpload(upload);
            const uploadResult = await upload.upload(file);
            onComplete(uploadResult);
        };

        const progressBg = getProgressBarColor(fileUpload?.uploadStatus);

        return (
            <div className={className}>
                <DragDropFileInput
                    title={file ? file.name : "Choose or drag file here"}
                    onChange={onFileChange}
                    readonly={!!file}
                />
                {fileUpload && fileUpload.uploadProgress !== null && (
                    <div className="progress mb-2">
                        <div
                            className={`progress-bar progress-bar-striped progress-bar-animated ${progressBg}`}
                            role="progressbar"
                            aria-valuenow={Math.trunc(
                                fileUpload.uploadProgress * 100
                            )}
                            aria-valuemin={0}
                            aria-valuemax={100}
                            style={{
                                width: `${Math.trunc(
                                    fileUpload.uploadProgress * 100
                                )}%`,
                            }}
                        />
                    </div>
                )}
                <button
                    disabled={!file || !!fileUpload}
                    onClick={() => upload(file)}
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
            </div>
        );
    }
);

interface UploadFormProps {
    packageSubmission: PackageSubmission;
}
const UploadForm: React.FC<UploadFormProps> = () => {
    const [uploadId, setUploadId] = useState<string | null>(null);
    const [communities, setCommunities] = useState<Community[]>([]);
    const [teams, setTeams] = useState<string[]>([]);

    const { register, handleSubmit } = useForm();

    const onSubmit = async () => {
        if (!uploadId) return;
        try {
            await ExperimentalApi.submitPackage({
                data: {
                    // TODO: Read from the form
                    upload_uuid: uploadId,
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

    useEffect(() => {
        ExperimentalApi.listCommunities().then((r) =>
            setCommunities(r.results)
        );
        ExperimentalApi.currentUser().then((r) => setTeams(r.teams));
    }, []);

    return (
        <div>
            <UploadHandler
                className={"mb-2"}
                onComplete={(uploadId) => setUploadId(uploadId)}
            />
            <form onSubmit={handleSubmit(onSubmit)}>
                <div>
                    <label htmlFor={"communities"}>Communities</label>
                    <select {...register("communities")}>
                        {communities.map((community) => (
                            <option
                                key={community.identifier}
                                value={community.identifier}
                            >
                                {community.name}
                            </option>
                        ))}
                    </select>
                </div>
                <div>
                    <label htmlFor={"teams"}>Team</label>
                    <select {...register("teams")}>
                        {teams.map((team) => (
                            <option key={team} value={team}>
                                {team}
                            </option>
                        ))}
                    </select>
                </div>

                <div>
                    <label htmlFor={"has_nsfw_content"}>
                        Contains NSFW content
                    </label>
                    <input
                        type={"checkbox"}
                        {...register("has_nsfw_content")}
                    />
                </div>

                <button
                    type={"submit"}
                    disabled={!uploadId}
                    className="btn btn-primary btn-block"
                >
                    Submit
                </button>
            </form>
        </div>
    );
};

interface ReadmePreviewProps {
    packageSubmission: PackageSubmission;
}
const ReadmePreview: React.FC<ReadmePreviewProps> = () => {
    return (
        <div className={"card bg-light mb-2"}>
            <div className={"card-header"}>README Preview</div>
            <div
                className={"card-body markdown-body"}
                dangerouslySetInnerHTML={{ __html: "" }}
            />
        </div>
    );
};

export const UploadPage: React.FC = () => {
    const packageSubmission = new PackageSubmission();

    return (
        <div>
            <div className="card bg-light mb-2">
                <div className="card-header">Upload Package</div>
                <div className="card-body py-2 px-2">
                    <UploadForm packageSubmission={packageSubmission} />
                </div>
            </div>
            <ReadmePreview packageSubmission={packageSubmission} />
        </div>
    );
};
