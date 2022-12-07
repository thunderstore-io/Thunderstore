import { PackageCategory } from "../../api";
import React, { PropsWithChildren, useContext, useState } from "react";

export type ContextProps = {
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

export interface IManagementContext {
    props: ContextProps;
    setCategories: (categories: PackageCategory[]) => void;
    closeModal: () => void;
}

export interface ManagementContextProviderProps {
    initial: ContextProps;
    closeModal: () => void;
}

export const ManagementContextProvider: React.FC<
    PropsWithChildren<ManagementContextProviderProps>
> = ({ children, initial, closeModal }) => {
    const [state, setState] = useState<ContextProps>(initial);

    const setCategories = (categories: PackageCategory[]) => {
        setState({
            ...state,
            currentCategories: categories,
        });
    };

    return (
        <ManagementContext.Provider
            value={{
                props: state,
                setCategories,
                closeModal,
            }}
        >
            {children}
        </ManagementContext.Provider>
    );
};
export const ManagementContext = React.createContext<
    IManagementContext | undefined
>(undefined);

export const useManagementContext = (): IManagementContext => {
    return useContext(ManagementContext)!;
};
