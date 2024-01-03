import { ReviewStatus } from "../../api";
import React, { PropsWithChildren, useContext } from "react";

export type ContextProps = {
    reviewStatus: ReviewStatus;
    rejectionReason: string;
    packageListingId: string;
    internalNotes: string;
};

export interface IReviewContext {
    props: ContextProps;
    closeModal: () => void;
}

export interface ManagementContextProviderProps {
    initial: ContextProps;
    closeModal: () => void;
}

export const ReviewContextProvider: React.FC<
    PropsWithChildren<ManagementContextProviderProps>
> = ({ children, initial, closeModal }) => {
    return (
        <ReviewContext.Provider
            value={{
                props: initial,
                closeModal,
            }}
        >
            {children}
        </ReviewContext.Provider>
    );
};
export const ReviewContext = React.createContext<IReviewContext | undefined>(
    undefined
);

export const useReviewContext = (): IReviewContext => {
    return useContext(ReviewContext)!;
};
