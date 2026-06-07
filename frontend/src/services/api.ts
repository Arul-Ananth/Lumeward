import { ApiError, apiRequest } from './http';

export interface BillingReceipt {
    deducted: number;
    remaining: number | string;
}

export interface NewsletterResponse {
    topic: string;
    content: string;
    bill: BillingReceipt;
}

export interface MemoryMetadata {
    topic?: string;
    sentiment?: string;
    timestamp?: string;
    user_id?: string;
    [key: string]: string | number | boolean | null | undefined;
}

export interface MemoryRecord {
    id: string;
    document: string;
    metadata: MemoryMetadata;
}

export interface FolderIngestResponse {
    status: string;
    batch_id: string;
    files_seen: number;
    files_ingested: number;
    files_skipped: number;
    files_failed: number;
    message: string;
}

interface RawMemoryRecord {
    id: string | number;
    document: string;
    metadata: MemoryMetadata;
}

interface ProfileResponse {
    memories: RawMemoryRecord[];
}

function normalizeMemory(item: RawMemoryRecord, index: number): MemoryRecord {
    const fallbackId = `${item.metadata.topic || 'memory'}-${index}`;
    return {
        id: String(item.id || fallbackId),
        document: item.document,
        metadata: item.metadata || {},
    };
}

export const api = {
    generateBriefing: async (topic: string, apiKeys?: { serper?: string; openai?: string }): Promise<NewsletterResponse> => {
        try {
            return await apiRequest<NewsletterResponse>('/news/generate', {
                method: 'POST',
                body: {
                    topic,
                    serper_api_key: apiKeys?.serper,
                    openai_api_key: apiKeys?.openai,
                },
            });
        } catch (error) {
            if (error instanceof ApiError && error.status === 402) {
                throw new Error('Insufficient Credits. Please Top Up.');
            }
            throw error;
        }
    },

    sendFeedback: async (originalTopic: string, feedbackText: string, sentiment: string): Promise<void> => {
        await apiRequest('/news/feedback', {
            method: 'POST',
            body: {
                original_topic: originalTopic,
                feedback_text: feedbackText,
                sentiment,
            },
        });
    },

    getProfile: async (): Promise<MemoryRecord[]> => {
        const data = await apiRequest<ProfileResponse>('/news/profile');
        const items = Array.isArray(data.memories) ? data.memories : [];
        return items.map(normalizeMemory);
    },

    uploadFolderZip: async (file: File): Promise<FolderIngestResponse> => {
        const formData = new FormData();
        formData.append('file', file);
        return apiRequest<FolderIngestResponse>('/news/ingest/folder', {
            method: 'POST',
            body: formData,
        });
    },
};
