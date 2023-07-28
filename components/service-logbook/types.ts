export interface Note {
  _id: string;
  /** User.publicId */
  user: string;
  text: string;
  /** unix epoch in milliseconds */
  created_on: number;
}

export interface NoteCBCResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
};
