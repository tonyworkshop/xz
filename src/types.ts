/**
 * 知识星球数据类型定义
 */

export interface Author {
  user_id: string;
  name: string;
  avatar_url?: string;
}

export interface Image {
  image_id?: string;
  large?: {
    url: string;
  };
  large_url?: string;
  original?: {
    url: string;
  };
}

export interface File {
  file_id: string;
  name: string;
  download_url: string;
  size?: number;
}

export interface Talk {
  text: string;
  images?: Image[];
  files?: File[];
}

export interface Question {
  text: string;
  images?: Image[];
}

export interface Answer {
  text: string;
  images?: Image[];
}

export interface Comment {
  comment_id: string;
  create_time: string;
  owner: Author;
  text: string;
  images?: Image[];
  replies?: Reply[];
  repliee?: Author;
}

export interface Reply {
  reply_id: string;
  create_time: string;
  owner: Author;
  text: string;
  images?: Image[];
  repliee?: Author;
}

export interface Like {
  user_id: string;
  name: string;
}

export interface Topic {
  topic_id: string;
  create_time: string;
  author: Author;
  talk?: Talk;
  question?: Question;
  answer?: Answer;
  type: 'talk' | 'question' | 'answer' | 'q&a' | 'task' | 'solution';
  comments?: Comment[];
  likes?: Like[];
  likes_count?: number;
  reads_count?: number;
  comments_count?: number;
}

export interface Config {
  group_id: string;
  group_name: string;
  target_author: string;
  output_dir: string;
  api_base_url: string;
}

export interface SyncedTopic {
  last_updated: string;
  comment_count: number;
}

export interface SyncState {
  last_sync_time: string | null;
  synced_topics: Record<string, SyncedTopic>;
  xu_zhe_user_id: string | null;
  full_sync_progress?: {
    in_progress: boolean;
    oldest_time: string | null; // 已下载到的最早时间戳
    total_downloaded: number;   // 已下载的帖子总数
  };
}

export interface ApiResponse {
  succeeded: boolean;
  resp_data?: {
    topics?: Topic[];
    topic?: Topic;
  };
}

export type SyncMode = 'full' | 'incremental' | 'open';
