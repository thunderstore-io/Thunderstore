import React, { CSSProperties } from "react";
import { useReportModalContext } from "./ReportModalContext";
import { useOnEscape } from "../../hooks/useOnEscape";
import { ReportForm, useReportForm } from "./hooks";
import { FormSelectField } from "../FormSelectField";
import { FieldError } from "react-hook-form/dist/types";

const Header: React.FC = () => {
    const context = useReportModalContext();

    return (
        <div className="modal-header">
            <div className="modal-title">Submit Report</div>
            <button
                type="button"
                className="close"
                aria-label="Close"
                onClick={context.closeModal}
                ref={(element) => element?.focus()}
            >
                <span aria-hidden="true">&times;</span>
            </button>
        </div>
    );
};

function getErrorMessage(error: FieldError): string {
    if (error.message) return error.message;
    switch (error.type) {
        case "required":
            return "This field is required";
        case "maxLength":
            return "Max length exceeded";
        default:
            return "Unknown error";
    }
}

const FieldError: React.FC<{ error?: FieldError }> = ({ error }) => {
    if (!error) return null;
    return <span className={"mt-1 text-danger"}>{getErrorMessage(error)}</span>;
};

interface BodyProps {
    form: ReportForm;
}

const Body: React.FC<BodyProps> = ({ form }) => {
    const context = useReportModalContext().props;

    return (
        <div className="modal-body gap-2 d-flex flex-column">
            <div className={"d-flex flex-column gap-1"}>
                <label className={"mb-0"}>Report reason</label>
                <FormSelectField
                    className={"select-category"}
                    control={form.control}
                    name={"reason"}
                    data={context.reasonChoices}
                    getOption={(x) => x}
                    required={true}
                />
                <FieldError error={form.fieldErrors?.reason} />
            </div>
            <div className={"d-flex flex-column gap-1"}>
                <label className={"mb-0"}>Description (optional)</label>
                <textarea
                    {...form.control.register("description", {
                        maxLength: context.descriptionMaxLength,
                    })}
                    className={"code-input"}
                    style={{ minHeight: "100px", fontFamily: "inherit" }}
                />
                <FieldError error={form.fieldErrors?.description} />
            </div>

            {form.error && (
                <div className={"alert alert-danger mt-2 mb-0"}>
                    <p className={"mb-0"}>{form.error}</p>
                </div>
            )}
            {form.status === "SUBMITTING" && (
                <div className={"alert alert-warning mt-2 mb-0"}>
                    <p className={"mb-0"}>Submitting...</p>
                </div>
            )}
            {form.status === "SUCCESS" && (
                <div className={"alert alert-success mt-2 mb-0"}>
                    <p className={"mb-0"}>Report submitted successfully!</p>
                </div>
            )}
        </div>
    );
};

interface FooterProps {
    form: ReportForm;
}

const Footer: React.FC<FooterProps> = ({ form }) => {
    return (
        <div className="modal-footer d-flex justify-content-end">
            <button
                type="button"
                className="btn btn-danger"
                disabled={
                    form.status === "SUBMITTING" || form.status === "SUCCESS"
                }
                onClick={form.onSubmit}
            >
                Submit
            </button>
        </div>
    );
};
export const ReportModal: React.FC = () => {
    const context = useReportModalContext();
    useOnEscape(context.closeModal);

    const form = useReportForm(
        context.props.packageListingId,
        () => {} // TODO: Indicate success, prevent double-submission
    );

    const style = {
        backgroundColor: "rgba(0, 0, 0, 0.4)",
        display: "block",
    } as CSSProperties;
    return (
        <div
            className="modal"
            role="dialog"
            style={style}
            onClick={context.closeModal}
        >
            <div
                className="modal-dialog modal-dialog-centered"
                role="document"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="modal-content">
                    <Header />
                    <Body form={form} />
                    <Footer form={form} />
                </div>
            </div>
        </div>
    );
};
