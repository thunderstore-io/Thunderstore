import * as crypto from "crypto-js";

export function getCookie(name: string) {
    let cookieValue = null;
    if (document.cookie && document.cookie != "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            let cookie = cookies[i];
            if (!cookie) continue;
            cookie = cookie.trim();

            if (cookie.substring(0, name.length + 1) == name + "=") {
                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1)
                );
                break;
            }
        }
    }
    return cookieValue;
}

export function calculateMD5(blob: Blob): Promise<string> {
    return new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const md5 = crypto.MD5(
                crypto.enc.Latin1.parse(reader.result!.toString())
            );
            resolve(md5.toString(crypto.enc.Base64));
        };
        reader.readAsBinaryString(blob);
    });
}

export function sleep(ms: number): Promise<undefined> {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseXhrResponseHeaders(allHeaders: string): Headers {
    const result = new Headers();
    allHeaders
        .trim()
        .split(/[\r\n]+/)
        .map((value) => value.split(/: /))
        .forEach((kvp) => {
            if (kvp.length == 2 && kvp[0] && kvp[1]) {
                result.set(kvp[0], kvp[1]);
            }
        });
    return result;
}

interface FetchOptions extends RequestInit {
    headers?: Headers;
}
export function fetchWithProgress(
    url: string,
    opts: FetchOptions = {},
    onProgress?: (this: XMLHttpRequest, ev: ProgressEvent) => any
): Promise<Response> {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open(opts.method || "get", url);

        if (opts.headers) {
            opts.headers.forEach((val, key) => {
                xhr.setRequestHeader(key, val);
            });
        }

        xhr.onload = () => {
            const headers = parseXhrResponseHeaders(
                xhr.getAllResponseHeaders()
            );
            resolve(
                new Response(xhr.response, {
                    status: xhr.status,
                    statusText: xhr.statusText,
                    headers: headers,
                })
            );
        };
        xhr.onerror = reject;
        if (xhr.upload && onProgress) xhr.upload.onprogress = onProgress;
        xhr.send(opts.body);
    });
}
