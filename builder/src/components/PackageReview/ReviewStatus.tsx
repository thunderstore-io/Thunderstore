import React from "react";
import { ReviewStatus } from "../../api";

interface PackageStatusProps {
    reviewStatus: ReviewStatus;
}

function getStatusClassName(status: ReviewStatus) {
    switch (status) {
        case "approved":
            return "text-success";
        case "unreviewed":
            return "text-warning";
        case "rejected":
            return "text-danger";
    }
}

export const ReviewStatusDisplay: React.FC<PackageStatusProps> = ({
    reviewStatus,
}) => {
    return (
        <div className={`text-capitalize ${getStatusClassName(reviewStatus)}`}>
            {reviewStatus}
        </div>
    );
};
