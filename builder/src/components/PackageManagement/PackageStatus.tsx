import React from "react";

interface PackageStatusProps {
    isDeprecated: boolean;
}

export const PackageStatus: React.FC<PackageStatusProps> = (props) => {
    const text = props.isDeprecated ? "Deprecated" : "Active";
    const className = props.isDeprecated ? "text-warning" : "text-success";

    return <div className={className}>{text}</div>;
};
