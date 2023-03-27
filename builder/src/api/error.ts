import { JSONValue } from "./models";

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
    response: Response;
    errorObject: JSONValue | null;

    constructor(
        message: string,
        response: Response,
        errorObject: JSONValue | null
    ) {
        this.message = message;
        this.response = response;
        this.errorObject = errorObject;
    }

    static createFromResponse = async (message: string, response: Response) => {
        let errorObject: JSONValue | null = null;
        try {
            errorObject = await response.json();
        } catch (e) {
            console.error(e);
        }
        return new ThunderstoreApiError(message, response, errorObject);
    };

    public toString(): string {
        if (this.errorObject) {
            const detail = JSON.stringify(this.errorObject, undefined, 2);
            return `${this.message} - ${detail}`;
        } else {
            return `${this.message}`;
        }
    }

    get statusCode(): number {
        return this.response.status;
    }

    get statusText(): string {
        return this.response.statusText;
    }
}
