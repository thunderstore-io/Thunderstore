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
import { Control } from "react-hook-form/dist/types";

function getUploadProgressBarcolor(uploadStatus: FileUploadStatus | undefined) {
    if (uploadStatus == FileUploadStatus.CANCELED) {
        return "bg-warning";
    } else if (uploadStatus == FileUploadStatus.ERRORED) {
        return "bg-danger";
    } else if (uploadStatus == FileUploadStatus.COMPLETE) {
        return "bg-success";
    }
    return "bg-info";
}

function getSubmissionProgressBarcolor(
    submissionStatus: SubmissionStatus | null
) {
    if (submissionStatus == SubmissionStatus.COMPLETE) {
        return "bg-success";
    } else if (submissionStatus == SubmissionStatus.ERROR) {
        return "bg-danger";
    }
    return "bg-warning";
}

class FormErrors {
    fileError: string | null = null;
    teamError: string | null = null;
    communitiesError: string | null = null;
    categoriesError: string | null = null;
    nsfwError: string | null = null;
    generalError: string | null = null;

    get hasErrors(): boolean {
        return !(
            this.fileError == null &&
            this.teamError == null &&
            this.communitiesError == null &&
            this.categoriesError == null &&
            this.nsfwError == null &&
            this.generalError == null
        );
    }
}

interface FormRowProps {
    label: string;
    labelFor: string;
    error: string | null;
}
const FormRow: React.FC<FormRowProps> = (props) => {
    return (
        <div className="field-wrapper">
            <div className="field-row">
                <label htmlFor={props.labelFor}>{props.label}</label>
                {props.children}
            </div>
            {props.error && (
                <div className="text-danger field-errors">{props.error}</div>
            )}
        </div>
    );
};

interface ProgressBarProps {
    className: string;
    progress: number;
}
const ProgressBar: React.FC<ProgressBarProps> = observer(
    ({ className, progress }) => {
        return (
            <div className="progress my-2">
                <div
                    className={`progress-bar progress-bar-striped progress-bar-animated ${className}`}
                    role="progressbar"
                    aria-valuenow={progress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    style={{
                        width: `${progress}%`,
                    }}
                />
            </div>
        );
    }
);

interface FormSelectFieldProps<T> {
    control: Control;
    name: string;
    data: T[];
    getOption: (t: T) => { value: string; label: string };
    default?: T;
    isMulti?: boolean;
}
const FormSelectField: React.FC<FormSelectFieldProps<any>> = (props) => {
    const defaultValue = props.default
        ? props.isMulti
            ? [props.getOption(props.default)]
            : props.getOption(props.default)
        : undefined;

    return (
        <div className="w-100">
            <div style={{ color: "#666" }}>
                <Controller
                    name={props.name}
                    control={props.control}
                    defaultValue={defaultValue}
                    render={({ field }) => (
                        <Select
                            {...field}
                            isMulti={props.isMulti || false}
                            defaultValue={defaultValue}
                            options={props.data.map(props.getOption)}
                        />
                    )}
                />
            </div>
            {props.children}
        </div>
    );
};

enum SubmissionStatus {
    UPLOADING = "UPLOADING",
    PROCESSING = "PROCESSING",
    COMPLETE = "COMPLETE",
    ERROR = "ERROR",
}

interface SubmissionFormProps {
    onSubmissionComplete?: (result: PackageSubmissionResult) => void;
}
const SubmissionForm: React.FC<SubmissionFormProps> = observer((props) => {
    const [communities, setCommunities] = useState<Community[] | null>(null);
    const [categories, setCategories] = useState<PackageCategory[] | null>(
        null
    );
    const [currentCommunity, setCurrentCommunity] = useState<Community | null>(
        null
    );
    const [teams, setTeams] = useState<string[] | null>(null);
    const [formErrors, setFormErrors] = useState<FormErrors>(new FormErrors());
    const [file, setFile] = useState<File | null>(null);
    const [fileUpload, setFileUpload] = useState<FileUpload | null>(null);
    const [
        submissionStatus,
        setSubmissionStatus,
    ] = useState<SubmissionStatus | null>(null);

    const { register, handleSubmit, control } = useForm();
    useOnBeforeUnload(!!file);

    const cancel = async () => {
        setFile(null);
        if (fileUpload) {
            await fileUpload.cancelUpload();
        }
        setFileUpload(null);
        setSubmissionStatus(null);
    };

    const upload = async (file: File | null) => {
        if (!file) return;
        const upload = new FileUpload();
        setFileUpload(upload);
        return await upload.upload(file);
    };

    const onFileChange = (files: FileList) => {
        const file = files.item(0);
        setFile(file);
    };

    const onSubmit = async (data: any) => {
        // TODO: Convert to react-hook-form validation
        setFormErrors(new FormErrors());
        const errors = new FormErrors();

        const uploadTeam = data.team ? data.team.value : null;
        const uploadCommunities = data.communities
            ? data.communities.map((com: any) => com.value)
            : [];
        const uploadCategories = data.categories
            ? data.categories.map((cat: any) => cat.value)
            : [];
        const uploadNsfw = !!data.has_nsfw_content;

        if (uploadTeam == null) {
            errors.teamError = "Selecting a team is required";
        }
        if (uploadCommunities.length <= 0) {
            errors.communitiesError =
                "Selecting at least a single community is required";
        }

        if (errors.hasErrors) {
            setFormErrors(errors);
            return;
        }

        setSubmissionStatus(SubmissionStatus.UPLOADING);
        try {
            const uploadId = await upload(file);
            if (!uploadId) return;
            setSubmissionStatus(SubmissionStatus.PROCESSING);
            const result = await ExperimentalApi.submitPackage({
                data: {
                    upload_uuid: uploadId,
                    author_name: uploadTeam,
                    categories: uploadCategories,
                    communities: uploadCommunities,
                    has_nsfw_content: uploadNsfw,
                },
            });
            setSubmissionStatus(SubmissionStatus.COMPLETE);
            if (props.onSubmissionComplete) {
                props.onSubmissionComplete(result);
            }
        } catch (e) {
            setSubmissionStatus(SubmissionStatus.ERROR);
            console.log(e);
        }
    };

    const uploadProgressBg = getUploadProgressBarcolor(
        fileUpload?.uploadStatus
    );
    const submissionProgressBg = getSubmissionProgressBarcolor(
        submissionStatus
    );
    const submissionProgress =
        submissionStatus && submissionStatus != SubmissionStatus.UPLOADING
            ? 100
            : 0;

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
            <div className="mb-2">
                <DragDropFileInput
                    title={file ? file.name : "Choose or drag file here"}
                    onChange={onFileChange}
                    readonly={!!file}
                />
            </div>

            {currentCommunity != null &&
            teams != null &&
            communities != null &&
            categories != null ? (
                <form onSubmit={handleSubmit(onSubmit)}>
                    <div className={"px-3 py-3"}>
                        <FormRow
                            label={"Team"}
                            labelFor={"team"}
                            error={formErrors.teamError}
                        >
                            <FormSelectField
                                control={control}
                                name={"team"}
                                data={teams}
                                getOption={(x) => {
                                    return { value: x, label: x };
                                }}
                            >
                                <p className="mt-1 mb-2">
                                    No teams available?{" "}
                                    <a href="/settings/teams/" className="ml-1">
                                        Create one here!
                                    </a>
                                </p>
                            </FormSelectField>
                        </FormRow>

                        <FormRow
                            label={"Communities"}
                            labelFor={"communities"}
                            error={formErrors.communitiesError}
                        >
                            <FormSelectField
                                control={control}
                                name={"communities"}
                                data={communities}
                                getOption={(x) => {
                                    return {
                                        value: x.identifier,
                                        label: x.name,
                                    };
                                }}
                                default={currentCommunity}
                                isMulti={true}
                            />
                        </FormRow>

                        <FormRow
                            label={"Categories"}
                            labelFor={"categories"}
                            error={formErrors.categoriesError}
                        >
                            <FormSelectField
                                control={control}
                                name={"categories"}
                                data={categories}
                                getOption={(x) => {
                                    return {
                                        value: x.slug,
                                        label: x.name,
                                    };
                                }}
                                isMulti={true}
                            >
                                <p className="mt-1 mb-2">
                                    Note that the selected categories are
                                    applied only to the
                                    <kbd className="text-info">
                                        {currentCommunity.name}
                                    </kbd>{" "}
                                    community. If you need to add categories to
                                    other communities, upload via their
                                    respective site instead.
                                </p>
                            </FormSelectField>
                        </FormRow>

                        <FormRow
                            label={"Contains NSFW content"}
                            labelFor={"has_nsfw_content"}
                            error={formErrors.nsfwError}
                        >
                            <input
                                type={"checkbox"}
                                {...register("has_nsfw_content")}
                            />
                        </FormRow>
                    </div>

                    <button
                        type={"submit"}
                        disabled={!file || !!fileUpload}
                        className="btn btn-primary btn-block"
                    >
                        Submit
                    </button>
                    <button
                        disabled={
                            !file ||
                            submissionStatus == SubmissionStatus.COMPLETE ||
                            submissionStatus == SubmissionStatus.PROCESSING
                        }
                        onClick={cancel}
                        className="btn btn-danger btn-block"
                    >
                        Cancel
                    </button>

                    {fileUpload && fileUpload.uploadProgress !== null && (
                        <ProgressBar
                            className={uploadProgressBg}
                            progress={Math.trunc(
                                fileUpload.uploadProgress * 100
                            )}
                        />
                    )}
                    {submissionStatus !== null && (
                        <ProgressBar
                            className={submissionProgressBg}
                            progress={submissionProgress}
                        />
                    )}
                </form>
            ) : (
                <div className={"px-3 py-3"}>
                    <p>Loading...</p>
                </div>
            )}
        </div>
    );
});

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
                        <thead>
                            <tr>
                                <th>Community</th>
                                <th>Link</th>
                                <th>Categories</th>
                            </tr>
                        </thead>
                        <tbody>
                            {result.available_communities.map((listingInfo) => (
                                <SubmissionResultRow
                                    key={listingInfo.url}
                                    info={listingInfo}
                                />
                            ))}
                        </tbody>
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
