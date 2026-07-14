import { apiRequest } from './http';

export interface NewsletterResponse {
    topic: string;
    content: string;
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

export interface Workspace {
    id: number;
    organization_id: number;
    name: string;
    slug: string;
    role: 'member' | 'workspace_admin';
    organization_role: 'member' | 'organization_admin';
}

export interface Tag {
    id: number;
    organization_id: number;
    normalized_key: string;
    display_name: string;
}

export interface FeedCard {
    id: number;
    title: string;
    bullets: string[];
    topics: string[];
    priority_score: number;
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
    listWorkspaces: () => apiRequest<Workspace[]>('/auth/workspaces'),

    createOrganization: (name: string, slug: string) => apiRequest<{ id: number }>('/auth/organizations', {
        method: 'POST', body: { name, slug },
    }),

    createWorkspace: (organizationId: number, name: string, slug: string) => apiRequest<Workspace>('/auth/workspaces', {
        method: 'POST', body: { organization_id: organizationId, name, slug },
    }),

    addMember: async (workspace: Workspace, email: string): Promise<void> => {
        await apiRequest(`/auth/organizations/${workspace.organization_id}/members`, {
            method: 'POST', body: { email, role: 'member' },
        });
        await apiRequest(`/auth/workspaces/${workspace.id}/members`, {
            method: 'POST', body: { email, role: 'member' },
        });
    },

    listTags: (workspaceId: number) => apiRequest<Tag[]>(`/auth/workspaces/${workspaceId}/tags`),

    createTag: (organizationId: number, displayName: string) => apiRequest<Tag>('/auth/tags', {
        method: 'POST', body: { organization_id: organizationId, display_name: displayName },
    }),

    setTagPreference: (tagId: number, weight: number, muted: boolean) => apiRequest(`/auth/tags/${tagId}/preference`, {
        method: 'PUT', body: { weight, muted },
    }),

    shareContext: (text: string, title: string, tagIds: number[]) => apiRequest<{ chunks_indexed: number }>('/news/ingest/context', {
        method: 'POST', body: { text, title, tag_ids: tagIds, source: 'web' },
    }),

    getFeed: () => apiRequest<FeedCard[]>('/news/feed'),

    generateBriefing: async (topic: string): Promise<NewsletterResponse> => {
        return apiRequest<NewsletterResponse>('/news/generate', {
            method: 'POST',
            body: { topic },
        });
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
