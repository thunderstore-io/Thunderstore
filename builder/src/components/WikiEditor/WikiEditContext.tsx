import React, { PropsWithChildren, useContext, useState } from "react";
import { MarkdownPreviewProvider } from "./MarkdownPreviewContext";
import {
    BaseApiError,
    ExperimentalApi,
    ThunderstoreApiError,
    WikiDeleteError,
    WikiPageUpsertError,
    WikiPageUpsertRequest,
} from "../../api";
import { useOnBeforeUnload } from "../../state/OnBeforeUnload";
import * as Sentry from "@sentry/browser";

type EditorOptions = {
    titleMaxLength: number;
    markdownMaxLength: number;
};

type PageData = {
    id?: string | number;
    title: string;
    markdown_content: string;
};

type ErrorList = { [key: string]: string[] } | {};
type ParsedErrors<Fields> = {
    fields: Fields;
    general: string[];
};

type FieldErrors = {
    title: string[];
    markdown: string[];
};

export type WikiEditErrors = ParsedErrors<FieldErrors>;

export type IWikiEditContext = {
    page: PageData;
    package: {
        namespace: string;
        name: string;
    };
    errors?: WikiEditErrors;
    setErrors: (errors?: WikiEditErrors) => void;
    options: EditorOptions;
    setMarkdown: (markdown: string) => void;
    setTitle: (title: string) => void;
    clearCache: () => void;
    isSubmitting: boolean;
    setIsSubmitting: (val: boolean) => void;
    wikiUrl: string;
    upsertPage: () => void;
    deletePage?: () => void;
};

type PartialContext = Omit<IWikiEditContext, "upsertPage" | "deletePage">;

export interface WikiEditContextProviderProps {
    pkg: {
        namespace: string;
        name: string;
    };
    page: WikiPageUpsertRequest | null;
    options: EditorOptions;
    wikiUrl: string;
}

const useStoredState = (
    enabled: boolean,
    storageKey: string,
    defaultVal: string
): [() => string, (val: string) => string, () => void] => {
    if (enabled) {
        return [
            () => {
                return localStorage.getItem(storageKey) ?? defaultVal;
            },
            (val: string) => {
                localStorage.setItem(storageKey, val);
                return val;
            },
            () => localStorage.removeItem(storageKey),
        ];
    } else {
        return [() => defaultVal, (val: string) => val, () => undefined];
    }
};

function parseApiError<
    ErrorType extends ErrorList & BaseApiError,
    Fields extends ErrorList
>(
    e: unknown | ThunderstoreApiError,
    mapErrors: (e: ErrorType) => Partial<ParsedErrors<Fields>>
) {
    let errors: ParsedErrors<Fields> = {
        fields: {} as Fields,
        general: [],
    };

    if (e instanceof ThunderstoreApiError) {
        const error = e.errorObject as ErrorType | null;
        if (error) {
            errors = { ...errors, ...mapErrors(error) };
            errors.general.push(...(error.non_field_errors ?? []));
            errors.general.push(...(error.__all__ ?? []));
        } else {
            Sentry.captureException(e);
            errors.general.push("Unknown error occurred");
            console.error(e);
        }
    } else {
        Sentry.captureException(e);
        errors.general.push("Unknown error occurred");
        console.error(e);
    }
    return errors;
}

const upsertPage = (context: PartialContext) => {
    if (context.isSubmitting) return;
    context.setIsSubmitting(true);
    context.setErrors(undefined);
    ExperimentalApi.upsertPackageWikiPage({
        namespace: context.package.namespace,
        name: context.package.name,
        data: context.page,
    })
        .then((resp) => {
            context.clearCache();
            window.location.replace(`${context.wikiUrl}${resp.slug}/`);
        })
        .catch((e) => {
            const errors = parseApiError<WikiPageUpsertError, FieldErrors>(
                e,
                (e) => ({
                    fields: {
                        title: e.title ?? [],
                        markdown: e.markdown_content ?? [],
                    },
                })
            );
            context.setErrors(errors);
        })
        .finally(() => context.setIsSubmitting(false));
};

const deletePage = (context: PartialContext & { page: { id: string } }) => {
    if (context.isSubmitting) return;
    if (
        !confirm(
            "You're about to delete a page, this action can't be undone. Are you sure?"
        )
    )
        return;
    context.setIsSubmitting(true);
    context.setErrors(undefined);
    ExperimentalApi.deletePackageWikiPage({
        namespace: context.package.namespace,
        name: context.package.name,
        pageId: context.page.id,
    })
        .then(() => {
            window.location.replace(`${context.wikiUrl}`);
        })
        .catch((e) => {
            const errors = parseApiError<WikiDeleteError, FieldErrors>(
                e,
                (e) => ({
                    general: e.pageId ?? [],
                })
            );
            context.setErrors(errors);
        })
        .finally(() => context.setIsSubmitting(false));
};

const hasPage = (
    context: PartialContext
): context is PartialContext & { page: { id: string } } => {
    return !!context.page.id;
};

export const WikiEditContextProvider: React.FC<
    PropsWithChildren<WikiEditContextProviderProps>
> = ({ children, page, pkg, options, wikiUrl }) => {
    const isNew = !page?.id;
    const [title, setTitle] = useState<string>(page?.title ?? "");
    const [errors, setErrors] = useState<WikiEditErrors | undefined>(undefined);
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [
        getStoredMarkdown,
        setStoredMarkdown,
        clearStoredMarkdown,
    ] = useStoredState(
        isNew,
        "legacy.wikiEditor.newPageMarkdown",
        page?.markdown_content ?? "# New page"
    );
    const [markdown, setMarkdown] = useState<string>(getStoredMarkdown);
    const _setMarkdown = (val: string) => setMarkdown(setStoredMarkdown(val));

    useOnBeforeUnload(
        !isNew && page?.markdown_content != markdown && !isSubmitting
    );

    const partialContext: PartialContext = {
        page: {
            id: page?.id,
            title,
            markdown_content: markdown,
        },
        package: pkg,
        options: options,
        errors,
        setErrors,
        setMarkdown: _setMarkdown,
        clearCache: clearStoredMarkdown,
        setTitle,
        isSubmitting,
        setIsSubmitting,
        wikiUrl,
    };
    const context: IWikiEditContext = {
        ...partialContext,
        upsertPage: () => upsertPage(partialContext),
        deletePage: hasPage(partialContext)
            ? () => deletePage(partialContext)
            : undefined,
    };

    return (
        <WikiEditContext.Provider value={context}>
            <MarkdownPreviewProvider markdown={markdown}>
                {children}
            </MarkdownPreviewProvider>
        </WikiEditContext.Provider>
    );
};
export const WikiEditContext = React.createContext<
    IWikiEditContext | undefined
>(undefined);

export const useWikiEditContext = (): IWikiEditContext => {
    return useContext(WikiEditContext)!;
};
