import React, { PropsWithChildren, useContext } from "react";

export interface CsrfTokenProviderProps {
    token: string;
}

export const CsrfTokenProvider: React.FC<
    PropsWithChildren<CsrfTokenProviderProps>
> = ({ children, token }) => {
    return (
        <CsrfTokenContext.Provider value={token}>
            {children}
        </CsrfTokenContext.Provider>
    );
};

export const CsrfTokenContext = React.createContext<string | undefined>(
    undefined
);

export const useCsrfToken = (): string => {
    return useContext(CsrfTokenContext)!;
};
