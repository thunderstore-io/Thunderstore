import React, { useEffect, useState } from "react";
import {
    Community,
    PackageCategory,
    ExperimentalApi,
    PackageSubmissionResult,
    PackageAvailableCommunity,
} from "./api";
import { useForm, Controller } from "react-hook-form";
import Select from "react-select";
import { DragDropFileInput } from "./components/DragDropFileInput";
import { FileUpload, FileUploadStatus } from "./state/FileUpload";
import { observer } from "mobx-react";
import { useOnBeforeUnload } from "./state/OnBeforeUnload";
import { PackageVersionHeader } from "./components/PackageVersionSummary";

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
        useOnBeforeUnload(!!file);

        const onFileChange = (files: FileList) => {
            const file = files.item(0);
            setFile(file);
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

interface SubmissionFormProps {
    onSubmissionComplete?: (result: PackageSubmissionResult) => void;
}
const SubmissionForm: React.FC<SubmissionFormProps> = (props) => {
    const [uploadId, setUploadId] = useState<string | null>(null);
    const [communities, setCommunities] = useState<Community[] | null>(null);
    const [categories, setCategories] = useState<PackageCategory[] | null>(
        null
    );
    const [currentCommunity, setCurrentCommunity] = useState<Community | null>(
        null
    );
    const [teams, setTeams] = useState<string[] | null>(null);

    const [teamError, setTeamError] = useState<string | null>(null);
    const [communitiesError, setCommunitiesError] = useState<string | null>(
        null
    );
    const [categoriesError, setCategoriesError] = useState<string | null>(null);
    const [nsfwError, setNsfwError] = useState<string | null>(null);

    const { register, handleSubmit, control } = useForm();

    const onSubmit = async (data: any) => {
        // TODO: Convert to react-hook-form validation
        setTeamError(null);
        setCommunitiesError(null);
        setCategoriesError(null);
        setNsfwError(null);

        const uploadTeam = data.team ? data.team.value : null;
        const uploadCommunities = data.communities
            ? data.communities.map((com: any) => com.value)
            : [];
        const uploadCategories = data.categories
            ? data.categories.map((cat: any) => cat.value)
            : [];
        const uploadNsfw = !!data.has_nsfw_content;

        let errored = false;
        if (uploadTeam == null) {
            setTeamError("Selecting a team is required");
            errored = true;
        }
        if (uploadCommunities.length <= 0) {
            setCommunitiesError(
                "Selecting at least a single community is required"
            );
            errored = true;
        }

        if (errored) {
            return;
        }

        if (!uploadId) return;
        try {
            const result = await ExperimentalApi.submitPackage({
                data: {
                    upload_uuid: uploadId,
                    author_name: uploadTeam,
                    categories: uploadCategories,
                    communities: uploadCommunities,
                    has_nsfw_content: uploadNsfw,
                },
            });
            if (props.onSubmissionComplete) {
                props.onSubmissionComplete(result);
            }
        } catch (e) {
            console.log(e);
        }
    };

    useEffect(() => {
        ExperimentalApi.listCommunities().then((r) =>
            setCommunities(r.results)
        );
        ExperimentalApi.currentUser().then((r) => setTeams(r.teams));
        ExperimentalApi.currentCommunity().then((community) => {
            setCurrentCommunity(community);
            ExperimentalApi.listCategories({
                communityIdentifier: community.identifier,
            }).then((r) => setCategories(r.results));
        });
    }, []);

    return (
        <div>
            <UploadHandler
                className={"mb-2"}
                onComplete={(uploadId) => setUploadId(uploadId)}
            />
            {currentCommunity != null &&
            teams != null &&
            communities != null &&
            categories != null ? (
                <form onSubmit={handleSubmit(onSubmit)}>
                    <div className={"px-3 py-3"}>
                        <div className="field-wrapper">
                            <div className="field-row">
                                <label htmlFor={"team"}>Team</label>
                                <div className="w-100">
                                    <div style={{ color: "#666" }}>
                                        <Controller
                                            name={"team"}
                                            control={control}
                                            render={({ field }) => (
                                                <Select
                                                    {...field}
                                                    options={teams.map(
                                                        (team) => {
                                                            return {
                                                                value: team,
                                                                label: team,
                                                            };
                                                        }
                                                    )}
                                                />
                                            )}
                                        />
                                    </div>
                                    <p className="mt-1 mb-2">
                                        No teams available?{" "}
                                        <a
                                            href="/settings/teams/"
                                            className="ml-1"
                                        >
                                            Create one here!
                                        </a>
                                    </p>
                                </div>
                            </div>
                            {teamError && (
                                <div className="text-danger field-errors">
                                    {teamError}
                                </div>
                            )}
                        </div>

                        <div className="field-wrapper">
                            <div className="field-row">
                                <label htmlFor={"communities"}>
                                    Communities
                                </label>
                                <div className="w-100">
                                    <div style={{ color: "#666" }}>
                                        <Controller
                                            name={"communities"}
                                            control={control}
                                            defaultValue={[
                                                {
                                                    value:
                                                        currentCommunity.identifier,
                                                    label:
                                                        currentCommunity.name,
                                                },
                                            ]}
                                            render={({ field }) => (
                                                <Select
                                                    {...field}
                                                    isMulti={true}
                                                    defaultValue={{
                                                        value:
                                                            currentCommunity.identifier,
                                                        label:
                                                            currentCommunity.name,
                                                    }}
                                                    options={communities.map(
                                                        (community) => {
                                                            return {
                                                                value:
                                                                    community.identifier,
                                                                label:
                                                                    community.name,
                                                            };
                                                        }
                                                    )}
                                                />
                                            )}
                                        />
                                    </div>
                                </div>
                            </div>
                            {communitiesError && (
                                <div className="text-danger field-errors">
                                    {communitiesError}
                                </div>
                            )}
                        </div>

                        <div className="field-wrapper">
                            <div className="field-row">
                                <label htmlFor="categories">Categories</label>
                                <div className="w-100">
                                    <div style={{ color: "#666" }}>
                                        <Controller
                                            name={"categories"}
                                            control={control}
                                            render={({ field }) => (
                                                <Select
                                                    {...field}
                                                    isMulti={true}
                                                    options={categories.map(
                                                        (category) => {
                                                            return {
                                                                value:
                                                                    category.slug,
                                                                label:
                                                                    category.name,
                                                            };
                                                        }
                                                    )}
                                                />
                                            )}
                                        />
                                    </div>
                                    <p className="mt-1 mb-2">
                                        Note that the selected categories are
                                        applied only to the
                                        <kbd className="text-info">
                                            {currentCommunity.name}
                                        </kbd>{" "}
                                        community. If you need to add categories
                                        to other communities, upload via their
                                        respective site instead.
                                    </p>
                                </div>
                            </div>
                            {categoriesError && (
                                <div className="text-danger field-errors">
                                    {categoriesError}
                                </div>
                            )}
                        </div>

                        <div className="field-wrapper">
                            <div className="field-row">
                                <label htmlFor={"has_nsfw_content"}>
                                    Contains NSFW content
                                </label>
                                <input
                                    type={"checkbox"}
                                    {...register("has_nsfw_content")}
                                />
                            </div>
                            {nsfwError && (
                                <div className="text-danger field-errors">
                                    {nsfwError}
                                </div>
                            )}
                        </div>
                    </div>

                    <button
                        type={"submit"}
                        disabled={!uploadId}
                        className="btn btn-primary btn-block"
                    >
                        Submit
                    </button>
                </form>
            ) : (
                <div className={"px-3 py-3"}>
                    <p>Loading...</p>
                </div>
            )}
        </div>
    );
};

interface PackageAvailableCommunityProps {
    info: PackageAvailableCommunity;
}
export const SubmissionResultRow: React.FC<PackageAvailableCommunityProps> = ({
    info,
}) => {
    return (
        <tr>
            <td>{info.community.name}</td>
            <td>
                <a href={info.url}>View listing</a>
            </td>
            <td>
                <div className="category-badge-container bg-light px-2 pt-2 flex-grow-1 d-flex flex-row flex-wrap align-items-end align-content-end ">
                    {info.categories.map((category) => {
                        return (
                            <span className="badge badge-pill badge-secondary category-badge">
                                {category.name}
                            </span>
                        );
                    })}
                </div>
            </td>
        </tr>
    );
};

interface SubmissionResultsProps {
    result: PackageSubmissionResult;
}
export const SubmissionResults: React.FC<SubmissionResultsProps> = ({
    result,
}) => {
    const communityCount = result.available_communities.length;
    const resultText =
        communityCount > 0
            ? communityCount > 1
                ? `The package is listed in ${communityCount} communities:`
                : `The package is listed in 1 community:`
            : `The package is not listed in any communities`;

    return (
        <React.Fragment>
            <PackageVersionHeader version={result.package_version} />
            <div className="card-body">
                <div>
                    <h3>Success!</h3>
                    <p>{resultText}</p>
                    <table className="table mb-0">
                        <tr>
                            <th>Community</th>
                            <th>Link</th>
                            <th>Categories</th>
                        </tr>
                        {result.available_communities.map((listingInfo) => (
                            <SubmissionResultRow info={listingInfo} />
                        ))}
                    </table>
                </div>
            </div>
        </React.Fragment>
    );
};

export const UploadPage: React.FC = () => {
    const [
        submissionResult,
        setSubmissionResult,
    ] = useState<PackageSubmissionResult | null>(null);

    const onSubmissionComplete = (result: PackageSubmissionResult) => {
        setSubmissionResult(result);
    };

    return (
        <div style={{ marginBottom: "96px" }}>
            {/* Bottom margin will affect how select option dropdowns render */}

            <div className="card bg-light mb-3">
                <div className="card-header">Submit Package</div>
                <div className="card-body py-2 px-2">
                    <SubmissionForm
                        onSubmissionComplete={onSubmissionComplete}
                    />
                </div>
            </div>
            {submissionResult ? (
                <div
                    className="card bg-light mb-3"
                    style={{ marginBottom: "96px" }}
                >
                    <SubmissionResults result={submissionResult} />
                </div>
            ) : null}
        </div>
    );
};
