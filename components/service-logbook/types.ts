export interface ServiceLogbookCategory {
  id: number;
  name: string;
  translate?: boolean;
  color?: string;
}

export interface Note {
  _id: string;
  /**
   * User.publicId
   *
   * @deprecated
   */
  user?: string;
  subject: string | null;
  text: string;
  /** unix epoch in milliseconds */
  created_on: number;
  category: number | null;
  note_category: string | null;

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

  // Date field for moment of action
  performed_on: number | null;

  // Calibration & Settings update
  tag_number: string | null;

  // Software update
  version: string | null;
  software_type: string | null;
  external_note: boolean | null;

  // Stack replacements
  stack_replacements?: string | null;
  workorder_id: string | null;
}

export interface NoteWithHtml extends Note {
  html: string;
}
