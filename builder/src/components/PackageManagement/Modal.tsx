import React, { CSSProperties } from "react";
import { useManagementContext } from "./Context";
import {
    PackageListingUpdateForm,
    useOnEscape,
    usePackageListingUpdateForm,
} from "./hooks";
import { PackageStatus } from "./PackageStatus";
import { CategoriesSelect } from "./CategoriesSelect";
import { DeprecationForm } from "./Deprecation";

const Header: React.FC = () => {
    const context = useManagementContext();

    return (
        <div className="modal-header">
            <div className="modal-title">Manage Package</div>
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
    form: PackageListingUpdateForm;
}

const Body: React.FC<BodyProps> = (props) => {
    const context = useManagementContext().props;

    return (
        <div className="modal-body">
            <div className="alert alert-primary">
                Changes might take several minutes to show publicly! Info shown
                below is always up to date.
            </div>
            <form onSubmit={props.form.onSubmit}>
                <div className="mt-3">
                    <h6>Package Status</h6>
                    <PackageStatus isDeprecated={context.isDeprecated} />
                </div>
                {context.canUpdateCategories && (
                    <div className="mt-3">
                        <h6>Edit categories</h6>
                        <CategoriesSelect form={props.form} />
                    </div>
                )}
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
    form: PackageListingUpdateForm;
}

const Footer: React.FC<FooterProps> = (props) => {
    return (
        <div className="modal-footer d-flex justify-content-between">
            <DeprecationForm />
            <button
                type="button"
                className="btn btn-success"
                disabled={props.form.status === "SUBMITTING"}
                onClick={props.form.onSubmit}
            >
                Save changes
            </button>
        </div>
    );
};
export const PackageManagementModal: React.FC = () => {
    const context = useManagementContext();
    const form = usePackageListingUpdateForm(
        context.props.packageListingId,
        (result) => context.setCategories(result.categories)
    );
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
