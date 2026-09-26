export interface User {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  language_code: string;
  bio: string | null;
  created_at: string;
  updated_at: string | null;
}
