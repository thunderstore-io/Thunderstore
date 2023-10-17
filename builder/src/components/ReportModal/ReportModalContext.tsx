import React, { PropsWithChildren, useContext } from "react";

export type ReportModalContextProps = {
    csrfToken: string;
    packageListingId: string;
    reasonChoices: { value: string; label: string }[];
    descriptionMaxLength: number;
};

export interface IReportModalContext {
    props: ReportModalContextProps;
    closeModal: () => void;
}

export interface ReportModalContextProviderProps {
    initial: ReportModalContextProps;
    closeModal: () => void;
}

export const ReportModalContextProvider: React.FC<
    PropsWithChildren<ReportModalContextProviderProps>
> = ({ children, initial, closeModal }) => {
    return (
        <ReportModalContext.Provider value={{ props: initial, closeModal }}>
            {children}
        </ReportModalContext.Provider>
    );
};
export const ReportModalContext = React.createContext<
    IReportModalContext | undefined
>(undefined);

export const useReportModalContext = (): IReportModalContext => {
    return useContext(ReportModalContext)!;
};
