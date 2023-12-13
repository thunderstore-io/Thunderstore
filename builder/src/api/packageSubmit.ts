import { ExperimentalApi } from "./api";
import { PackageSubmissionData, PackageSubmissionResult } from "./models";
import { sleep } from "../utils";
import { ThunderstoreApiError } from "./error";

export async function SubmitPackage(props: {
    data: PackageSubmissionData;
    useAsyncFlow: boolean;
}): Promise<PackageSubmissionResult> {
    if (props.useAsyncFlow) {
        return SubmitPackageAsync(props.data);
    } else {
        return SubmitPackageSync(props.data);
    }
}

async function SubmitPackageAsync(data: PackageSubmissionData) {
    let submission = await ExperimentalApi.submitPackageAsync({ data });
    const submissionId = submission.id;
    let retriesLeft = 3;

    while (submission.status != "FINISHED") {
        await sleep(5000);
        try {
            submission = await ExperimentalApi.pollAsyncSubmission({
                submissionId,
            });
            retriesLeft = 3;
        } catch (e) {
            retriesLeft -= 1;
            if (retriesLeft < 0) {
                throw e;
            }
        }
    }

    if (submission.form_errors) {
        throw new ThunderstoreApiError(
            "Submission processing failed",
            null,
            submission.form_errors
        );
    }
    if (submission.task_error || !submission.result) {
        throw new Error("Package submission processing failed");
    }

    return submission.result;
}

async function SubmitPackageSync(data: PackageSubmissionData) {
    return await ExperimentalApi.submitPackage({ data });
}
