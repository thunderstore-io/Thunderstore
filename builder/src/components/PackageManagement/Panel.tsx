import React from "react";
import { DeprecationForm } from "./Deprecation";
import { CategoriesForm } from "./Categories";
import { PackageCategory } from "../../api";

type PackageManagementPanelProps = {
    isDeprecated: boolean;
    canDeprecate: boolean;
    canUndeprecate: boolean;
    canUnlist: boolean;
    canUpdateCategories: boolean;
    csrfToken: string;
    currentCategories: PackageCategory[];
    availableCategories: PackageCategory[];
    packageListingId: string;
};
export const PackageManagementPanel: React.FC<PackageManagementPanelProps> = (
    props
) => {
    const StatusText: React.FC = () => {
        if (props.isDeprecated) {
            return (
                <>
                    Current status:{" "}
                    <span className="badge badge-pill badge-danger">
                        deprecated
                    </span>
                </>
            );
        } else {
            return (
                <>
                    Current status:{" "}
                    <span className="badge badge-pill badge-primary">
                        active
                    </span>
                </>
            );
        }
    };

    return (
        <div className="card text-white bg-info mt-2">
            <div className="card-body">
                <h4 className="card-title">Manage package</h4>
                <p className="card-text">
                    Changes might take several minutes to show publicly! This
                    card is always up to date.
                </p>
                <div className="mt-3">
                    <h5>Status</h5>
                    <p className="card-text">
                        <StatusText />
                    </p>
                    <DeprecationForm {...props} />
                </div>
                <div className="mt-3">
                    <h5>Categories</h5>
                    <CategoriesForm {...props} />
                </div>
            </div>
        </div>
    );
};
