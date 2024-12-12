export interface Note {
  _id: string;
  /**
   * User.publicId
   *
   * @deprecated
   */
  user?: string;
  text: string;
  /** unix epoch in milliseconds */
  created_on: number;

  /** User.publicId */
  author_id: string | null;
  /** User.name */
  author_name: string | null;
  /** User.publicId */
  editor_id: string | null;
  /** User.name */
  editor_name: string | null;
  /** unix epoch in milliseconds */
  updated_on: number | null;
}

export interface NoteWithHtml extends Note {
  html: string;
}
