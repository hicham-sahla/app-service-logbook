export interface ServiceLogbookCategory {
  id: number;
  name: string;
  translate?: boolean;
  color?: string;
}

export interface StackReplacement {
  stack_identifier: string;
  removed_serial_number?: string;
  added_serial_number?: string;
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

  // Daily report
  additional_user: string | null;
  performed_on: number | null;
  week_number: number | null;
  worked_hours: number | null;
  mcps_worked_on: string | null;
  fcps_worked_on: string | null;
  owls_worked_on: string | null;

  // Calibrations
  tag_number: string | null;

  // Software changes

  // Stack replacements
  stack_replacements?: StackReplacement[];
}

export interface NoteWithHtml extends Note {
  html: string;
}
