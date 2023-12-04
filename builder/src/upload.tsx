import * as Sentry from "@sentry/browser";
import React, { useEffect, useState } from "react";
import {
    Community,
    ExperimentalApi,
    PackageAvailableCommunity,
    PackageCategory,
    PackageSubmissionResult,
    ThunderstoreApiError,
} from "./api";
import { useForm } from "react-hook-form";
import { DragDropFileInput } from "./components/DragDropFileInput";
import { FileUpload, FileUploadStatus } from "./state/FileUpload";
import { observer } from "mobx-react";
import { useOnBeforeUnload } from "./state/OnBeforeUnload";
import { PackageVersionHeader } from "./components/PackageVersionSummary";
import { ProgressBar } from "./components/ProgressBar";
import { FormSelectField } from "./components/FormSelectField";
import { CommunityCategorySelector } from "./components/CommunitySelector";
import { FormRow } from "./components/FormRow";

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
    generalErrors: string[] = [];

    get hasErrors(): boolean {
        return !(
            this.fileError == null &&
            this.teamError == null &&
            this.communitiesError == null &&
            this.categoriesError == null &&
            this.nsfwError == null &&
            this.generalErrors.length == 0
        );
    }
}

interface SubmissionError {
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

enum SubmissionStatus {
    UPLOADING = "UPLOADING",
    PROCESSING = "PROCESSING",
    COMPLETE = "COMPLETE",
    ERROR = "ERROR",
}

interface SubmissionFormProps {
    onSubmissionComplete?: (result: PackageSubmissionResult) => void;
    currentCommunity: Community;
}
const SubmissionForm: React.FC<SubmissionFormProps> = observer((props) => {
    const currentCommunity = props.currentCommunity;
    const [communities, setCommunities] = useState<Community[] | null>(null);
    const [categories, setCategories] = useState<PackageCategory[] | null>(
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

    const { register, handleSubmit, control, watch } = useForm();
    const {
        control: categoriesControl,
        getValues: getCategoriesFormValues,
    } = useForm<{
        [key: string]: { label: string; value: string }[] | undefined;
    }>();

    const transformSelectedCategories = () => {
        const untransformed = getCategoriesFormValues();
        const result: { [key: string]: string[] } = {};
        for (const [community, categories] of Object.entries(untransformed)) {
            if (!categories) continue;
            result[community] = categories.map((x) => x.value);
        }
        return result;
    };

    const selectedCommunities:
        | { value: string; label: string }[]
        | undefined = watch("communities", undefined);

    useOnBeforeUnload(!!file && submissionStatus != SubmissionStatus.COMPLETE);

    const cancel = async () => {
        setFile(null);
        if (fileUpload) {
            await fileUpload.cancelUpload();
        }
        setFileUpload(null);
        setSubmissionStatus(null);
        setFormErrors(new FormErrors());
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

        const uploadCategories = transformSelectedCategories();
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
            try {
                setSubmissionStatus(SubmissionStatus.PROCESSING);
                const result = await ExperimentalApi.submitPackage({
                    data: {
                        upload_uuid: uploadId,
                        author_name: uploadTeam,
                        community_categories: uploadCategories,
                        communities: uploadCommunities,
                        has_nsfw_content: uploadNsfw,
                    },
                });
                setSubmissionStatus(SubmissionStatus.COMPLETE);
                if (props.onSubmissionComplete) {
                    props.onSubmissionComplete(result);
                }
            } catch (e) {
                const errors = new FormErrors();
                if (e instanceof ThunderstoreApiError) {
                    const error = e.errorObject as SubmissionError | null;
                    if (error) {
                        if (error.upload_uuid) {
                            errors.generalErrors.push(...error.upload_uuid);
                        }
                        if (error.author_name) {
                            errors.teamError = error.author_name[0] || null;
                        }
                        if (error.team) {
                            errors.teamError = error.team[0] || null;
                        }
                        if (error.categories) {
                            errors.categoriesError =
                                error.categories[0] || null;
                        }
                        if (error.communities) {
                            errors.communitiesError =
                                error.communities[0] || null;
                        }
                        if (error.has_nsfw_content) {
                            errors.nsfwError =
                                error.has_nsfw_content[0] || null;
                        }
                        if (error.detail) {
                            errors.generalErrors.push(error.detail);
                        }
                        if (error.file) {
                            errors.generalErrors.push(...error.file);
                        }
                        if (error.__all__) {
                            errors.generalErrors.push(...error.__all__);
                        }
                    } else {
                        Sentry.captureException(e);
                        errors.generalErrors.push(
                            "Unknown error occurred while submitting package"
                        );
                        console.error(e);
                    }
                } else {
                    Sentry.captureException(e);
                    errors.generalErrors.push(
                        "Unknown error occurred while submitting package"
                    );
                    console.error(e);
                }
                setFormErrors(errors);
                setSubmissionStatus(SubmissionStatus.ERROR);
            }
        } catch (e) {
            Sentry.captureException(e);
            const errors = new FormErrors();
            errors.generalErrors.push(
                "Unknown error occurred while uploading file"
            );
            setFormErrors(errors);
            console.error(e);
        }
    };

    const hasErrors =
        (fileUpload?.uploadErrors ?? []).length > 0 ||
        formErrors.generalErrors.length > 0;

    const hasEtagError =
        fileUpload &&
        fileUpload.uploadErrors.some(
            (x) => x.indexOf("ETag: This field is required.") > 0
        );

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

    const enumerateCommunities = (current: Community[], cursor?: string) => {
        const promise = cursor
            ? ExperimentalApi.getNextPage<Community>(cursor)
            : ExperimentalApi.listCommunities();

        promise.then((result) => {
            const next = current.concat(result.results);
            setCommunities(next);
            if (result.pagination.next_link) {
                enumerateCommunities(next, result.pagination.next_link);
            }
        });
    };

    const enumerateCategories = (
        current: PackageCategory[],
        communityIdentifier: string,
        cursor?: string
    ) => {
        const promise = cursor
            ? ExperimentalApi.getNextPage<PackageCategory>(cursor)
            : ExperimentalApi.listCategories({ communityIdentifier });

        promise.then((result) => {
            const next = current.concat(result.results);
            setCategories(next);
            if (result.pagination.next_link) {
                enumerateCategories(
                    next,
                    communityIdentifier,
                    result.pagination.next_link
                );
            }
        });
    };

    useEffect(() => {
        ExperimentalApi.listCommunities().then((r) =>
            setCommunities(r.results)
        );
        enumerateCommunities([]);
        enumerateCategories([], currentCommunity.identifier);
        ExperimentalApi.currentUser().then((r) => setTeams(r.teams));
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
                                    The team name will become the prefix of the
                                    package ID. No teams available?{" "}
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
                            <CommunityCategorySelector
                                selectedCommunities={
                                    selectedCommunities ?? [
                                        {
                                            value: currentCommunity.identifier,
                                            label: currentCommunity.name,
                                        },
                                    ]
                                }
                                control={categoriesControl}
                            />
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
                    {hasErrors && (
                        <div className="mb-0 px-3 py-3 alert alert-danger field-errors">
                            <ul className="mx-0 my-0 pl-3">
                                {formErrors.generalErrors.map((e, idx) => (
                                    <li key={`general-${idx}`}>{e}</li>
                                ))}
                                {fileUpload?.uploadErrors.map((e, idx) => (
                                    <li key={`upload-${idx}`}>{e}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                    {hasEtagError && (
                        <div className="mb-0 mt-2 px-3 py-3 alert alert-info field-errors">
                            <p className="mx-0 my-0">
                                Some browser extensions such as ClearURLs strip
                                ETag response headers. Make sure this is not
                                happening e.g. by disabling extensions and try
                                again.
                            </p>
                        </div>
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
                <a href={info.url} target={"_blank"}>
                    View listing
                </a>
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

interface UploadPageProps {
    currentCommunity: Community;
}
export const UploadPage: React.FC<UploadPageProps> = (props) => {
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
                        currentCommunity={props.currentCommunity}
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
