import React from "react";
import { PackageVersion } from "../api";

const getDisplayName = (version: PackageVersion) => {
    return version.name.split("_").join(" ");
};

interface PackageVersionHeaderProps {
    version: PackageVersion;
}
export const PackageVersionHeader: React.FC<PackageVersionHeaderProps> = ({
    version,
}) => {
    return (
        <div className="card-header">
            <div className="media">
                {/* TODO: Add thumbnail scaling for icon when converting to NextJS */}
                <img
                    className="align-self-center mr-3"
                    style={{ width: 128, height: 128 }}
                    src={version.icon}
                    alt="icon"
                />
                <div className="media-body">
                    <h1 className="mt-0">{getDisplayName(version)}</h1>
                    <p>{version.description}</p>
                    <div className="d-flex w-100 justify-content-between">
                        <h5 className="mb-1">By {version.namespace}</h5>
                        {version.website_url ? (
                            <a
                                className="text-nowrap"
                                href={version.website_url}
                            >
                                <span className="fa fa-globe-americas fa-fw" />
                                {version.website_url}
                            </a>
                        ) : null}
                    </div>
                </div>
            </div>
        </div>
    );
};
