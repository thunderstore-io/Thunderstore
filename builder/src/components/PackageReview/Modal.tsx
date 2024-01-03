import React, { CSSProperties } from "react";
import { useReviewContext } from "./Context";
import { PackageListingReviewForm, usePackageReviewForm } from "./useForm";
import { ReviewStatusDisplay } from "./ReviewStatus";
import { useOnEscape } from "../common/useOnEscape";

const Header: React.FC = () => {
    const context = useReviewContext();

    return (
        <div className="modal-header">
            <div className="modal-title">Review Package</div>
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

interface BodyProps {
    form: PackageListingReviewForm;
}

const Body: React.FC<BodyProps> = (props) => {
    const context = useReviewContext();
    const state = context.props;

    return (
        <div className="modal-body">
            <div className="alert alert-primary">
                Changes might take several minutes to show publicly! Info shown
                below is always up to date.
            </div>
            <form
                onSubmit={(e) => {
                    e.preventDefault();
                }}
            >
                <div className="mt-3">
                    <h6>Review Status</h6>
                    <ReviewStatusDisplay reviewStatus={state.reviewStatus} />
                </div>
                <div className="mt-3">
                    <h6>Rejection reason (saved on reject)</h6>
                    <textarea
                        {...props.form.control.register("rejectionReason")}
                        className={"code-input"}
                        style={{ minHeight: "100px" }}
                    />
                </div>
                <div className="mt-3">
                    <h6>Internal notes</h6>
                    <textarea
                        {...props.form.control.register("internalNotes")}
                        className={"code-input"}
                        style={{ minHeight: "100px" }}
                    />
                </div>
            </form>
            {props.form.error && (
                <div className={"alert alert-danger mt-2 mb-0"}>
                    <p className={"mb-0"}>{props.form.error}</p>
                </div>
            )}
            {props.form.status === "SUBMITTING" && (
                <div className={"alert alert-warning mt-2 mb-0"}>
                    <p className={"mb-0"}>Saving...</p>
                </div>
            )}
            {props.form.status === "SUCCESS" && (
                <div className={"alert alert-success mt-2 mb-0"}>
                    <p className={"mb-0"}>Changes saved successfully!</p>
                </div>
            )}
        </div>
    );
};

interface FooterProps {
    form: PackageListingReviewForm;
}

const Footer: React.FC<FooterProps> = (props) => {
    return (
        <div className="modal-footer d-flex justify-content-between">
            <button
                type="button"
                className="btn btn-danger"
                disabled={props.form.status === "SUBMITTING"}
                onClick={props.form.reject}
            >
                Reject
            </button>
            <button
                type="button"
                className="btn btn-success"
                disabled={props.form.status === "SUBMITTING"}
                onClick={props.form.approve}
            >
                Approve
            </button>
        </div>
    );
};
export const PackageReviewModal: React.FC = () => {
    const context = useReviewContext();
    const form = usePackageReviewForm(context.props);
    useOnEscape(context.closeModal);

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
