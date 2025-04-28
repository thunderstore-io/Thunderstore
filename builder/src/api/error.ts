import { GenericApiError, JSONValue } from "./models";

export const stringifyError = (
    val: JSONValue | undefined,
    parents?: string[]
): string[] => {
    if (val === null) {
        return [];
    } else if (typeof val === "object") {
        const result = [];
        if (Array.isArray(val)) {
            for (const entry of val) {
                result.push(...stringifyError(entry, parents));
            }
        } else {
            Object.keys(val).forEach((key) => {
                result.push(
                    ...stringifyError(val[key]!, (parents || []).concat(key))
                );
            });
        }
        return result;
    } else {
        return [
            `${parents?.join(": ")}${parents ? ": " : ""}${
                val ? val.toString() : "Unknown error"
            }`,
        ];
    }
};

export class ThunderstoreApiError {
    message: string;
    response: Response | null;
    errorObject: JSONValue | null;
    extractedMessage: string | null;

    constructor(
        message: string,
        response: Response | null,
        errorObject: JSONValue | null,
        extractedMessage: string | null = null
    ) {
        this.message = message;
        this.response = response;
        this.errorObject = errorObject;
        this.extractedMessage = extractedMessage;
    }

    static createFromResponse = async (message: string, response: Response) => {
        let errorObject: JSONValue | null = null;
        let extractedMessage: string | null = null;
        try {
            errorObject = await response.json();
            if (typeof errorObject === "string") {
                extractedMessage = errorObject;
            } else if (typeof errorObject === "object") {
                const genericError = errorObject as GenericApiError;
                extractedMessage = genericError.detail || null;
            }
        } catch (e) {
            console.error(e);
        }
        return new ThunderstoreApiError(
            message,
            response,
            errorObject,
            extractedMessage
        );
    };

    public toString(): string {
        if (this.errorObject) {
            const detail = JSON.stringify(this.errorObject, undefined, 2);
            return `${this.message} - ${detail}`;
        } else {
            return `${this.message}`;
        }
    }

    get statusCode(): number | undefined {
        return this.response?.status;
    }

    get statusText(): string | undefined {
        return this.response?.statusText;
    }
}
