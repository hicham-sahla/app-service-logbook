<script lang="ts">
  import { onMount, tick } from "svelte";
  import {
    get,
    derived,
    writable,
    type Readable,
    type Writable,
  } from "svelte/store";
  import type {
    ComponentContext,
    ComponentInput,
    ResourceData,
    SingleSelectPanelOptions,
  } from "@ixon-cdk/types";
  import type { Note, NoteWithHtml, ServiceLogbookCategory } from "./types";
  import { NotesService } from "./notes.service";
  import { deburr, kebabCase } from "lodash-es";
  import { DateTime, type DateTimeFormatOptions } from "luxon";
  import {
    getFirstLetter,
    getStyle,
  } from "./letter-avatar/letter-avatar.utils";
  import { renderMarkdownToHtml } from "./formatters/markdown-to-html/markdown-to-html.utils";
  import { HtmlToReadableText } from "./service-logbook.utils";
  import {
    getCategoryStyle,
    mapAppConfigToServiceLogbookCategoryMapFactory,
  } from "./categories.utils";

  export let context: ComponentContext;

  let rootEl: HTMLDivElement;
  let addButton: HTMLButtonElement;
  let agentOrAsset: ResourceData.Agent | ResourceData.Asset | null = null;
  let agentOrAssetName: string | null = null;
  let categories: Map<number, ServiceLogbookCategory> = new Map();
  let myUser: ResourceData.MyUser | null = null;
  let loaded: Writable<boolean>;
  let mapAppConfigToServiceLogbookCategoryMap: (
    appConfig: ResourceData.AppConfig<{
      categories?: ServiceLogbookCategory[];
    }> | null
  ) => Map<number, ServiceLogbookCategory>;
  let notes: Writable<Note[]>;
  let notesWithHtml: Readable<NoteWithHtml[]>;
  let notesService: NotesService;
  let searchInput: HTMLInputElement | null = null;
  let searchInputVisible: boolean = false;
  let translations: Record<string, string> = {};
  let usersDict: Record<string, ResourceData.User> | null = null;
  let width: number | null = null;
  let now = DateTime.now();
  let dataVariableOptions: {
    value: string;
    label: string;
    shortLabel: string;
  }[] = [];
  const filter: Writable<{
    searchQuery: string | null;
    selectedCategoryId: number | null;
  }> = writable({
    searchQuery: null,
    selectedCategoryId: null,
  });

  let filteredNotesWithHtml: Readable<NoteWithHtml[]>;

  $: isNarrow = width !== null ? width <= 460 : false;
  $: isSmall = width !== null ? width <= 400 : false;
  $: notesWithCategories = derived([notesWithHtml], ([$notes]) => {
    return (
      categories.size > 0 &&
      ($notes?.some((note) => note.category !== undefined) ?? false)
    );
  });
  $: selectedCategoryName = derived([filter], ([$filter]) => {
    const category = getCategory($filter.selectedCategoryId);
    return category ? category.name : translations.CATEGORY;
  });

  function getStackCount(): number {
    if (!agentOrAssetName) return 5; // Default to 5MW if no agent

    // 1MW units have "EX425D" in their name
    if (agentOrAssetName.includes("EX425D")) {
      return 1;
    }

    // 5MW units have "EX2125D" in their name
    if (agentOrAssetName.includes("EX2125D")) {
      return 5;
    }

    // Default to 5MW if pattern not recognized
    return 5;
  }

  async function fetchDataVariables(
    agentId: string
  ): Promise<{ value: string; label: string; shortLabel: string }[]> {
    if (!agentId) return [];

    let allVariables: any[] = [];
    let moreAfter: string | null = null;

    try {
      do {
        const params: { [key: string]: string } = {
          agentId: agentId,
          "page-size": "1000", // Fetch in chunks of 1000
          fields: "name",
        };
        if (moreAfter) {
          params["page-after"] = moreAfter;
        }

        const url = context.getApiUrl("AgentDataVariableList", params);
        const response = await fetch(url, {
          headers: {
            Authorization: "Bearer " + context.appData.accessToken.secretId,
            "Api-Application": context.appData.apiAppId,
            "Api-Company": context.appData.company.publicId,
            "Api-Version": "2",
          },
          method: "GET",
        });

        const data = await response.json();

        if (data && data.data) {
          allVariables = allVariables.concat(data.data);
          moreAfter = data.moreAfter;
        } else {
          moreAfter = null;
        }
      } while (moreAfter);

      // Sort the combined data variables alphabetically by name
      const sortedVariables = allVariables.sort((a: any, b: any) => {
        return a.name.localeCompare(b.name, undefined, {
          numeric: true,
          sensitivity: "base",
        });
      });

      // Map the sorted data variables to options format
      return sortedVariables.map((variable: any) => ({
        value: variable.name,
        label: variable.name,
        shortLabel: variable.name,
      }));
    } catch (error) {
      console.error("Failed to fetch data variables:", error);
    }

    return [];
  }
  onMount(() => {
    translations = context.translate(
      [
        "ADD",
        "ADD_NOTE",
        "CATEGORY",
        "CONFIRM",
        "EDIT",
        "EDIT_NOTE",
        "EXPORT",
        "EXPORT_TO_CSV",
        "MORE_OPTIONS",
        "NO_NOTES",
        "NONE",
        "NOTE",
        "REMOVE",
        "REMOVE_NOTE",
        "SEARCH",
        "SERVICE_LOGBOOK",
        "SUBJECT",
        "UNCATEGORIZED", // Add this line
        "UNKNOWN_USER",
        "WHEN",
        "WHO",
        "__TEXT__.CONFIRM_NOTE_REMOVAL",
        "__TEXT__.NO_MATCHING_RESULTS",
        "IMPORT",
        "EXPORT",
        "IMPORT_FROM_JSON",
        "EXPORT_TO_JSON",
        "__TEXT__.CONFIRM_IMPORT",
      ],
      undefined,
      { source: "global" }
    );

    const backendComponentClient = context.createBackendComponentClient();
    mapAppConfigToServiceLogbookCategoryMap =
      mapAppConfigToServiceLogbookCategoryMapFactory(context);
    notesService = new NotesService(backendComponentClient);
    loaded = notesService.loaded;
    notes = notesService.notes;
    notesService.load();

    notesWithHtml = derived(notes, ($notes: Note[]) =>
      $notes.map((note) => {
        const html = note.text.match(/^<\/?[a-z][\s\S]*>/)
          ? note.text
          : renderMarkdownToHtml(note.text);
        return { ...note, html };
      })
    );

    filteredNotesWithHtml = derived(
      [filter, notesWithHtml],
      ([$filter, $notesWithHtml]) => {
        const { searchQuery, selectedCategoryId } = $filter;
        let notes =
          selectedCategoryId !== null
            ? $notesWithHtml.filter(
                (note) => note.category === selectedCategoryId
              )
            : $notesWithHtml;
        if (!searchQuery) {
          return notes;
        }

        const query = searchQuery.toLowerCase();
        return notes.filter((note) => {
          // Search in basic fields
          if (getNoteUserName(usersDict, note).toLowerCase().includes(query)) {
            return true;
          }
          if (note.subject?.toLowerCase().includes(query)) {
            return true;
          }
          if (HtmlToReadableText(note.html).toLowerCase().includes(query)) {
            return true;
          }

          // Search in category
          if (note.note_category?.toLowerCase().includes(query)) {
            return true;
          }

          // Search in tag number
          if (
            note.tag_numbers?.some((tag) => tag.toLowerCase().includes(query))
          ) {
            return true;
          }
          // Search in version
          if (note.version?.toLowerCase().includes(query)) {
            return true;
          }

          // Search in stack replacements (parse the string format)
          if (note.stack_replacements) {
            const stackSearchText = note.stack_replacements.toLowerCase();
            // Search directly in the formatted string
            if (stackSearchText.includes(query)) {
              return true;
            }

            // Also parse and search in individual fields
            const replacements = note.stack_replacements
              .split(";")
              .filter((r) => r.trim());

            for (const replacement of replacements) {
              const match = replacement.match(
                /\('([^']+)','([^']*)','([^']*)','([^']+)'\)/
              );
              if (match) {
                const [, identifier, removed, added, failed] = match;
                if (
                  identifier.toLowerCase().includes(query) ||
                  removed.toLowerCase().includes(query) ||
                  added.toLowerCase().includes(query) ||
                  (failed === "true" && "failed".includes(query))
                ) {
                  return true;
                }
              }
            }
          }
          // Search in stack inspections (parse the string format)
          if (note.stack_inspections) {
            const inspectionSearchText = note.stack_inspections.toLowerCase();
            // Search directly in the formatted string
            if (inspectionSearchText.includes(query)) {
              return true;
            }

            // Also parse and search in individual fields
            const inspections = note.stack_inspections
              .split(";")
              .filter((r) => r.trim());

            for (const inspection of inspections) {
              const match = inspection.match(
                /\('([^']+)','([^']*)','([^']*)','([^']*)'\)/
              );
              if (match) {
                const [, identifier, stackIdentifier, serialNumber, insight] =
                  match;
                if (
                  identifier.toLowerCase().includes(query) ||
                  stackIdentifier.toLowerCase().includes(query) ||
                  serialNumber.toLowerCase().includes(query) ||
                  insight.toLowerCase().includes(query)
                ) {
                  return true;
                }
              }
            }
          }
          // Search in external note flag
          if (note.external_note && "external".includes(query)) {
            return true;
          }

          return false;
        });
      }
    );

    const resourceDataClient = context.createResourceDataClient();
    resourceDataClient.query(
      [{ selector: "AppConfig", fields: ["values"] }],
      ([result]) => {
        const appConfig = result.data;
        categories = mapAppConfigToServiceLogbookCategoryMap(appConfig);
      }
    );
    resourceDataClient.query(
      [
        { selector: "Agent", fields: ["name", "permissions", "publicId"] },
        { selector: "Asset", fields: ["name", "permissions", "publicId"] },
      ],
      async ([agentResult, assetResult]) => {
        agentOrAsset = agentResult.data ?? assetResult.data;
        agentOrAssetName =
          assetResult.data?.name ?? agentResult.data?.name ?? "";

        // Fetch data variables if we have an agent
        if (agentResult.data?.publicId) {
          dataVariableOptions = await fetchDataVariables(
            agentResult.data.publicId
          );
        }
      }
    );
    resourceDataClient.query(
      [
        { selector: "MyUser", fields: ["publicId", "support"] },
        { selector: "UserList", fields: ["name", "publicId"] },
      ],
      ([myUserResult, userListResult]) => {
        myUser = myUserResult.data;
        if (userListResult.data) {
          usersDict = userListResult.data.reduce(
            (dict, user) => ({ ...dict, [user.publicId]: user }),
            {}
          );
        }
      }
    );

    createTooltip(addButton, { message: translations.ADD_NOTE });

    width = rootEl.getBoundingClientRect().width;
    const resizeObserver = new ResizeObserver((entries) => {
      entries.forEach((entry) => {
        width = entry.contentRect.width;
      });
    });
    resizeObserver.observe(rootEl);
    const unsubscribe = filteredNotesWithHtml.subscribe((notes) => {
      if (notes && notes.length > 0) {
        console.log("--- Currently Displayed Notes ---");
        console.table(notes);
      }
    });
    return () => {
      resizeObserver.unobserve(rootEl);
      unsubscribe();
    };
  });

  function getNoteIsActionable(
    _agentOrAsset: ResourceData.Agent | ResourceData.Asset | null,
    _myUser: ResourceData.MyUser | null,
    note: Note
  ): boolean {
    // Anyone can edit any note - restriction removed
    return true;
  }

  function getNoteUserName(
    _usersDict: Record<string, ResourceData.User> | null,
    note: Note
  ): string {
    if (_usersDict) {
      /**
       * If the note has an author_id, use the author_id to get the user name.
       * If the note has an author_name, use the author_name.
       * If the note has a user, use the user to get the user name.
       * If none of the above, use the UNKNOWN_USER translation.
       */
      return (
        (note.author_id ? _usersDict[note.author_id]?.name : null) ??
        note.author_name ??
        (note.user ? _usersDict[note.user]?.name : null) ??
        translations.UNKNOWN_USER
      );
    }
    return "";
  }

  function getNoteEditedBy(
    _usersDict: Record<string, ResourceData.User> | null,
    note: Note
  ): string {
    if (_usersDict && note.editor_id && note.editor_name) {
      /**
       * If the note has an editor_id, use the editor_id to get the user name.
       * If the note has an editor_name, use the editor_name.
       * If none of the above, return an empty string.
       */
      return _usersDict[note.editor_id]?.name ?? note.editor_name ?? "";
    }
    return "";
  }

  async function handleAddButtonClick(): Promise<void> {
    const categories = [
      "Calibration",
      "Software update",
      "Settings change",
      "Stack replacements",
      "Stack inspection",
      "Other",
    ];
    let step = "category";
    let category: string | null = null;
    let performed_on: string | null = null;
    let date: DateTime | null = null;

    while (step !== "exit") {
      if (step === "category") {
        const categoryResult = await context.openFormDialog({
          title: "Select a category",
          inputs: [
            {
              key: "category",
              type: "Selection",
              label: "Category",
              required: true,
              options: categories.map((c) => ({ label: c, value: c })),
            },
          ],
          submitButtonText: "Next",
          cancelButtonText: "Cancel",
        });

        if (categoryResult && categoryResult.value) {
          category = categoryResult.value.category;
          step = "note";
        } else {
          step = "exit";
        }
      } else if (step === "note") {
        if (!category) {
          step = "category";
          continue;
        }
        const noteResult = await context.openFormDialog({
          title: `${translations.ADD} ${category}`,
          inputs: _getNoteInputs(category),
          submitButtonText: translations.ADD,
          cancelButtonText: "Previous",
          discardChangesPrompt: true,
        });
        if (noteResult && noteResult.value) {
          const { value } = noteResult;
          const noteData: Partial<Note> = {
            note_category: category,
            external_note: value.external_note ?? false,
          };
          // Removed the old 'Stack replacements' specific date handling block (lines 89-91 original)

          if (category === "Stack replacements") {
            const stackReplacements: string[] = [];
            const stackCount = getStackCount();
            const allStackIdentifiers = ["a", "b", "c", "d", "e"];
            const stackIdentifiers = allStackIdentifiers.slice(0, stackCount);
            for (const identifier of stackIdentifiers) {
              const group = value[`stack_group_${identifier}`] || {};
              const removed_serial_number =
                group[`removed_serial_number_${identifier}`] || "";
              const added_serial_number =
                group[`added_serial_number_${identifier}`] || "";
              const stack_symptom = group[`stack_symptom_${identifier}`] || "";
              const stack_symptom_confirmed = group[
                `stack_symptom_confirmed_${identifier}`
              ]
                ? "true"
                : "false";
              if (removed_serial_number || added_serial_number) {
                stackReplacements.push(
                  `('${identifier}','${removed_serial_number}','${added_serial_number}','${stack_symptom}','${stack_symptom_confirmed}')`
                );
              }
            }

            if (stackReplacements.length > 0) {
              noteData.stack_replacements = stackReplacements.join(";") + ";";
            }
          }
          if (category === "Stack inspection") {
            const stackInspections: string[] = [];
            const stackCount = getStackCount();
            const allStackIdentifiers = ["a", "b", "c", "d", "e"];
            const stackIdentifiers = allStackIdentifiers.slice(0, stackCount);
            for (const identifier of stackIdentifiers) {
              const group = value[`stack_group_inspection_${identifier}`] || {};
              const stack_identifier =
                group[`stack_identifier_${identifier}`] || "";
              const stack_serial_number =
                group[`stack_serial_number_${identifier}`] || "";
              const insight = group[`insight_${identifier}`] || "";

              if (stack_identifier || stack_serial_number || insight) {
                stackInspections.push(
                  `('${identifier}','${stack_identifier}','${stack_serial_number}','${insight}')`
                );
              }
            }

            if (stackInspections.length > 0) {
              noteData.stack_inspections = stackInspections.join(";") + ";";
            }
          }
          // Transform tag_numbers from array of objects to array of strings
          if (value.tag_numbers && Array.isArray(value.tag_numbers)) {
            value.tag_numbers = value.tag_numbers.map((item: any) =>
              typeof item === "string" ? item : item.tag_number
            );
          }

          // FIX: Universal performed_on handling for all categories
          if (value.performed_on) {
            const performedOnDate = DateTime.fromISO(value.performed_on);
            if (performedOnDate.isValid) {
              noteData.performed_on = performedOnDate.toMillis();
            }
          }

          // Merge the rest of the form values
          const { performed_on, ...restOfValue } = value;
          Object.assign(noteData, restOfValue);
          notesService.add(noteData);
          step = "exit";
        } else {
          step = "category";
        }
      }
    }
  }

  async function handleDownloadCsvButtonClick(notes: Note[]): Promise<void> {
    const categories = Array.from(
      new Set(notes.map((n) => n.note_category).filter(Boolean))
    );
    const categoryOptions = categories.map((c) => ({ label: c, value: c }));

    const filterResult = await context.openFormDialog({
      title: "Export Options",
      inputs: [
        {
          key: "category",
          type: "Selection",
          label: "Filter by Category",
          options: [{ label: "All", value: "all" }, ...categoryOptions],
        },
      ],
      submitButtonText: "Next",
    });

    if (filterResult && filterResult.value) {
      const { category } = filterResult.value;

      let filteredNotes = notes;

      if (category && category !== "all") {
        filteredNotes = filteredNotes.filter(
          (note) => note.note_category === category
        );
      }

      const hasEditedBy = filteredNotes.some(
        (note) => note.editor_id && note.editor_name
      );
      const hasSubject = filteredNotes.some((note) => note.subject);
      const csvHeaders = [
        translations.WHO,
        translations.WHEN,
        ...(hasSubject ? [translations.SUBJECT] : []),
        ...(notesWithCategories ? [translations.CATEGORY] : []),
        translations.NOTE,
        ...(hasEditedBy
          ? [context.translate("EDITED_BY_USER", { user: "" })]
          : []),
      ];
      const csvData = filteredNotes.map((note) => [
        `"${getNoteUserName(usersDict, note)}"`,
        `"${mapNoteToWhenDateTime(note)}"`,
        ...(hasSubject ? [`"${note.subject?.replace(/"/g, "'") ?? "-"}"`] : []),
        ...(notesWithCategories
          ? [`"${getCategory(note.category)?.name ?? "-"}"`]
          : []),
        `"${note.text.replace(/"/g, "'")}"`,
        ...(hasEditedBy
          ? [`"${getNoteEditedBy(usersDict, note) ?? "-"}"`]
          : []),
      ]);
      const csvContent = `${[csvHeaders, ...csvData]
        .map((row) => row.join(","))
        .join("\n")}`;
      const data = new Blob([csvContent], { type: "text/csv" });
      const fileName = `${kebabCase(deburr(agentOrAssetName ?? undefined))}_service-logbook-notes.csv`;
      if ("saveAsFile" in context) {
        context.saveAsFile(data, fileName);
      }
    }
  }

  async function handlePreviewNoteClick(
    initialNote: NoteWithHtml
  ): Promise<void> {
    let root: ShadowRoot;
    let note: NoteWithHtml | null | undefined = initialNote;
    const previewNotes = get(filteredNotesWithHtml);
    await context.openContentDialog({
      htmlContent: getNoteHtmlContent(note),
      onopened(shadowRoot, close) {
        root = shadowRoot;
        const categoryElement = shadowRoot.querySelector(".category");
        if (categoryElement) {
          createTooltipOnEllipsis(categoryElement as HTMLElement);
        }

        const moreButton = shadowRoot.querySelector(".more");
        moreButton?.addEventListener("click", (event) => {
          if (note) {
            handleMoreActionsButtonClick(event, note, close);
          }
        });
        createTooltip(moreButton as HTMLButtonElement, {
          message: translations.MORE_OPTIONS,
        });
      },
      pagination: {
        pageCount: previewNotes.length,
        initialPageIndex: previewNotes.indexOf(note),
        onpagechange: (index) => {
          note = previewNotes.at(index);
          if (root && note) {
            updateNoteHtmlContent(root, note);
          }
        },
      },
      styles: `
          .card {
            height: 100%;
            border: 1px solid color-mix(in srgb, transparent, currentcolor 12%);
            border-radius: 8px;
            padding: 8px 16px;
            box-sizing: border-box;
            overflow: auto;

            .card-header {
              display: flex;
              flex-wrap: wrap;
              font-size: 0.8em;
              line-height: 1.3em;
              padding: 8px 16px;

              .note-info {
                display: flex;
                flex-direction: column;
              }

              .who {
                flex-direction: row;
                align-items: center;

                > span {
                  display: flex;
                  flex-direction: column;
                }

                .name {
                  font-size: 1.1em;
                  font-weight: 500;
                }
              }

              .when-what {
                align-items: end;
                margin: 3px 8px 0 auto;
                text-align: right;
              }

              .category {
                padding: 4px 8px;
                border-radius: 4px;
                max-width: 100px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
              }
            }

            .card-content {
              padding: 8px 16px;
              overflow-x: auto;

              div:empty {
                display: inline-block;
              }
            }

            .user-avatar {
              border-radius: 100%;
              margin-right: 8px;

              text {
                fill: #f5f5f5;
                font-family: Roboto, Helvetica Neue, sans-serif;
                font-size: 0.9em;
                font-weight: 300;
              }
            }

            .icon-button {
              box-sizing: border-box;
              position: relative;
              user-select: none;
              cursor: pointer;
              outline: 0;
              border: none;
              background-color: transparent;
              -webkit-tap-highlight-color: transparent;
              display: inline-block;
              white-space: nowrap;
              text-decoration: none;
              text-align: center;
              margin: 0;
              overflow: visible;
              padding: 0;
              width: 20px;
              height: 20px;
              flex-shrink: 0;
              line-height: 20px;
              border-radius: 50%;
              vertical-align: middle;
              color: currentcolor;

              svg {
                fill: currentcolor;
              }
            }
          }

          @media screen and (min-width: 960px) {
            .card {
              width: 860px;
            }
          }`,
    });
  }

  async function handleRemoveNoteButtonClick(note: Note): Promise<void> {
    const confirmed = await context.openConfirmDialog({
      title: translations.REMOVE_NOTE,
      message: translations["__TEXT__.CONFIRM_NOTE_REMOVAL"],
      confirmButtonText: translations.REMOVE,
      confirmCheckbox: true,
      destructive: true,
    });
    if (confirmed) {
      notesService.remove(note._id);
    }
  }

  async function handleMoreActionsButtonClick(
    event: Event,
    note: Note,
    closeDialog?: () => void
  ): Promise<void> {
    event.stopImmediatePropagation();
    const actions = [
      { type: "edit", title: translations.EDIT },
      { type: "recategorize", title: "Recategorize" }, // Add this line
      { type: "export", title: translations.EXPORT },
      { type: "remove", title: translations.REMOVE, destructive: true },
    ].filter((action) => {
      switch (action.type) {
        case "edit":
        case "remove":
        case "recategorize": // Add this line
          return getNoteIsActionable(agentOrAsset, myUser, note);
        default:
          return true;
      }
    });
    const target = event.target as HTMLElement;
    const result = await context.openActionMenu(target, {
      actions,
    });
    if (result) {
      const resultAction = actions[result.index];
      switch (resultAction?.type) {
        case "edit":
          handleEditNoteButtonClick(note);
          if (closeDialog) {
            closeDialog();
          }
          break;
        case "recategorize": // Add this new case
          handleRecategorizeNoteButtonClick(note);
          if (closeDialog) {
            closeDialog();
          }
          break;
        case "export":
          handleDownloadCsvButtonClick([note]);
          break;
        case "remove":
          handleRemoveNoteButtonClick(note);
          if (closeDialog) {
            closeDialog();
          }
          break;
      }
    }
  }

  async function handleEditNoteButtonClick(note: Note): Promise<void> {
    const performed_on_date = note.performed_on
      ? DateTime.fromMillis(note.performed_on)
      : null;

    const initialValue: any = {
      ...note,
      performed_on: performed_on_date ? performed_on_date.toISO() : undefined,
    };
    // Transform tag_numbers from array of strings to List format for display
    if (initialValue.tag_numbers && Array.isArray(initialValue.tag_numbers)) {
      initialValue.tag_numbers = initialValue.tag_numbers.map(
        (tag: string) => ({
          tag_number: tag,
        })
      );
    }
    if (
      note.note_category === "Stack replacements" &&
      note.stack_replacements
    ) {
      const replacements = note.stack_replacements
        .split(";")
        .filter((r) => r.trim())
        .map((r) => {
          const match = r.match(
            /\('([^']+)','([^']*)','([^']*)','([^']*)','([^']+)'\)/
          );
          if (match) {
            return {
              stack_identifier: match[1],
              removed_serial_number: match[2],
              added_serial_number: match[3],
              stack_symptom: match[4],
              stack_symptom_confirmed: match[5] === "true",
            };
          }
          return null;
        })
        .filter((r) => r !== null);

      for (const replacement of replacements) {
        if (replacement) {
          const identifier = replacement.stack_identifier;
          initialValue[`stack_group_${identifier}`] = {
            [`removed_serial_number_${identifier}`]:
              replacement.removed_serial_number,
            [`added_serial_number_${identifier}`]:
              replacement.added_serial_number,
            [`stack_symptom_${identifier}`]: replacement.stack_symptom,
            [`stack_symptom_confirmed_${identifier}`]:
              replacement.stack_symptom_confirmed,
          };
        }
      }
    }
    if (note.note_category === "Stack inspection" && note.stack_inspections) {
      const inspections = note.stack_inspections
        .split(";")
        .filter((r) => r.trim())
        .map((r) => {
          const match = r.match(/\('([^']+)','([^']*)','([^']*)','([^']*)'\)/);
          if (match) {
            return {
              stack_identifier: match[1],
              stack_identifier_value: match[2],
              stack_serial_number: match[3],
              insight: match[4],
            };
          }
          return null;
        })
        .filter((r) => r !== null);

      for (const inspection of inspections) {
        if (inspection) {
          const identifier = inspection.stack_identifier;
          initialValue[`stack_group_inspection_${identifier}`] = {
            [`stack_identifier_${identifier}`]:
              inspection.stack_identifier_value,
            [`stack_serial_number_${identifier}`]:
              inspection.stack_serial_number,
            [`insight_${identifier}`]: inspection.insight,
          };
        }
      }
    }
    const result = await context.openFormDialog({
      title: `${translations.EDIT} ${note.note_category}`,
      inputs: _getNoteInputs(note.note_category || "Other", true),
      initialValue,
      submitButtonText: translations.CONFIRM,
      discardChangesPrompt: true,
    });

    if (result && result.value) {
      const { performed_on, ...rest } = result.value;
      const updatedNote: Partial<Note> = { ...rest };

      if (performed_on) {
        const date = DateTime.fromISO(performed_on);
        updatedNote.performed_on = date.toMillis();
      }
      // Transform tag_numbers from array of objects to array of strings
      if (updatedNote.tag_numbers && Array.isArray(updatedNote.tag_numbers)) {
        updatedNote.tag_numbers = updatedNote.tag_numbers.map((item: any) =>
          typeof item === "string" ? item : item.tag_number
        );
      }
      if (note.note_category === "Stack replacements") {
        const stackReplacements: string[] = [];
        const stackCount = getStackCount();
        const allStackIdentifiers = ["a", "b", "c", "d", "e"];
        const stackIdentifiers = allStackIdentifiers.slice(0, stackCount);

        for (const identifier of stackIdentifiers) {
          const group = result.value[`stack_group_${identifier}`] || {};
          const removed_serial_number =
            group[`removed_serial_number_${identifier}`] || "";
          const added_serial_number =
            group[`added_serial_number_${identifier}`] || "";
          const stack_symptom = group[`stack_symptom_${identifier}`] || "";
          const stack_symptom_confirmed = group[
            `stack_symptom_confirmed_${identifier}`
          ]
            ? "true"
            : "false";

          if (removed_serial_number || added_serial_number) {
            stackReplacements.push(
              `('${identifier}','${removed_serial_number}','${added_serial_number}','${stack_symptom}','${stack_symptom_confirmed}')`
            );
          }
        }

        if (stackReplacements.length === 0) {
          context.openAlertDialog({
            title: "Validation Error",
            message: "At least one stack replacement must be filled in.",
          });
          return;
        }

        updatedNote.stack_replacements = stackReplacements.join(";") + ";";
      }
      if (note.note_category === "Stack inspection") {
        const stackInspections: string[] = [];
        const stackCount = getStackCount();
        const allStackIdentifiers = ["a", "b", "c", "d", "e"];
        const stackIdentifiers = allStackIdentifiers.slice(0, stackCount);

        for (const identifier of stackIdentifiers) {
          const group =
            result.value[`stack_group_inspection_${identifier}`] || {};
          const stack_identifier =
            group[`stack_identifier_${identifier}`] || "";
          const stack_serial_number =
            group[`stack_serial_number_${identifier}`] || "";
          const insight = group[`insight_${identifier}`] || "";

          if (stack_identifier || stack_serial_number || insight) {
            stackInspections.push(
              `('${identifier}','${stack_identifier}','${stack_serial_number}','${insight}')`
            );
          }
        }

        if (stackInspections.length === 0) {
          context.openAlertDialog({
            title: "Validation Error",
            message: "At least one stack inspection must be filled in.",
          });
          return;
        }

        updatedNote.stack_inspections = stackInspections.join(";") + ";";
      }
      await notesService.edit(note._id, updatedNote);
    }
  }
  async function handleRecategorizeNoteButtonClick(note: Note): Promise<void> {
    const categories = [
      "Calibration",
      "Software update",
      "Settings change",
      "Stack replacements",
      "Stack inspection",
      "Other",
    ];

    let step = "select_category";
    let newCategory: string | null = null;

    while (step !== "exit") {
      // Step 1: Select new category
      if (step === "select_category") {
        const categoryResult = await context.openFormDialog({
          title: "Recategorize Note - Select New Category",
          inputs: [
            {
              key: "new_category",
              type: "Selection",
              label: "New Category",
              required: true,
              options: categories.map((c) => ({ label: c, value: c })),
              description:
                "Choose the category you want to recategorize this note to",
            },
          ],
          submitButtonText: "Next: Fill New Fields",
          cancelButtonText: "Cancel",
        });

        if (categoryResult && categoryResult.value) {
          newCategory = categoryResult.value.new_category;
          step = "fill_new_fields";
        } else {
          step = "exit";
        }
      }
      // Step 2: Fill in new category fields (with current details visible at top)
      else if (step === "fill_new_fields") {
        if (!newCategory) {
          step = "select_category";
          continue;
        }

        // Build inputs array with current note details at top (disabled/read-only)
        const allInputs: ComponentInput[] = [];

        // === CURRENT NOTE DETAILS SECTION (READ-ONLY) ===
        allInputs.push({
          key: "separator_current",
          type: "String",
          label: "━━━━━ CURRENT NOTE (for reference) ━━━━━",
          defaultValue: "",
          disabled: true,
        });

        allInputs.push({
          key: "current_category_display",
          type: "String",
          label: "Current Category",
          defaultValue: note.note_category || "Other",
          disabled: true,
        });

        // Show performed_on if exists
        if (note.performed_on) {
          const performed_on_date = DateTime.fromMillis(note.performed_on);
          allInputs.push({
            key: "current_performed_on",
            type: "String",
            label: "Current Performed On",
            defaultValue: performed_on_date.toLocaleString(DateTime.DATE_SHORT),
            disabled: true,
          });
        }

        // Show category-specific current fields based on note category
        switch (note.note_category) {
          case "Calibration":
          case "Settings change":
            if (note.tag_numbers && note.tag_numbers.length > 0) {
              allInputs.push({
                key: "current_tag_numbers",
                type: "String",
                label: "Current Tag Numbers",
                defaultValue: note.tag_numbers.join(", "),
                disabled: true,
              });
            }
            break;

          case "Software update":
            if (note.software_type) {
              allInputs.push({
                key: "current_software_type",
                type: "String",
                label: "Current Software Type",
                defaultValue: note.software_type,
                disabled: true,
              });
            }
            if (note.version) {
              allInputs.push({
                key: "current_version",
                type: "String",
                label: "Current Version",
                defaultValue: note.version,
                disabled: true,
              });
            }
            break;

          case "Stack replacements":
            if (note.workorder_id) {
              allInputs.push({
                key: "current_workorder_id",
                type: "String",
                label: "Current Workorder ID",
                defaultValue: note.workorder_id,
                disabled: true,
              });
            }
            if (note.stack_replacements) {
              allInputs.push({
                key: "current_stack_replacements",
                type: "String",
                label: "Current Stack Replacements",
                defaultValue: note.stack_replacements,
                disabled: true,
              });
            }
            break;

          case "Stack inspection":
            if (note.stack_inspections) {
              allInputs.push({
                key: "current_stack_inspections",
                type: "String",
                label: "Current Stack Inspections",
                defaultValue: note.stack_inspections,
                disabled: true,
              });
            }
            break;
        }

        // Show current text (description)
        allInputs.push({
          key: "current_text",
          type: "String",
          label: "Current Description",
          defaultValue:
            note.text.replace(/<[^>]*>/g, "").substring(0, 200) +
            (note.text.length > 200 ? "..." : ""),
          disabled: true,
        });

        // Show external note status
        if (note.external_note) {
          allInputs.push({
            key: "current_external_note",
            type: "String",
            label: "Current External Note",
            defaultValue: "Yes",
            disabled: true,
          });
        }

        // === NEW CATEGORY FIELDS SECTION (EDITABLE) ===
        allInputs.push({
          key: "separator_new",
          type: "String",
          label: `━━━━━ NEW ${newCategory.toUpperCase()} FIELDS ━━━━━`,
          defaultValue: "",
          disabled: true,
        });

        // Add the new category's input fields
        const newCategoryInputs = _getNoteInputs(newCategory, true);
        allInputs.push(...newCategoryInputs);

        const newFieldsResult = await context.openFormDialog({
          title: `Recategorize to ${newCategory}`,
          inputs: allInputs,
          initialValue: {
            // Preserve common fields
            performed_on: note.performed_on
              ? DateTime.fromMillis(note.performed_on).toISODate()
              : null,
            text: note.text,
            external_note: note.external_note ?? false,
          },
          submitButtonText: "Recategorize Note",
          cancelButtonText: "Previous",
          discardChangesPrompt: true,
        });

        if (newFieldsResult && newFieldsResult.value) {
          const { value } = newFieldsResult;
          const updatedNote: Partial<Note> = {
            note_category: newCategory,
            text: value.text,
            external_note: value.external_note ?? false,
          };

          // Handle performed_on
          if (value.performed_on) {
            const date = DateTime.fromISO(value.performed_on);
            updatedNote.performed_on = date.toMillis();
          }

          // Clear old category-specific fields
          updatedNote.tag_numbers = null;
          updatedNote.version = null;
          updatedNote.software_type = null;
          updatedNote.stack_replacements = null;
          updatedNote.stack_inspections = null;
          updatedNote.workorder_id = null;

          // Handle new category-specific fields
          switch (newCategory) {
            case "Calibration":
            case "Settings change":
              if (value.tag_numbers && Array.isArray(value.tag_numbers)) {
                updatedNote.tag_numbers = value.tag_numbers.map((item: any) =>
                  typeof item === "string" ? item : item.tag_number
                );
              }
              break;

            case "Software update":
              updatedNote.software_type = value.software_type || null;
              updatedNote.version = value.version || null;
              break;

            case "Stack replacements":
              updatedNote.workorder_id = value.workorder_id || null;
              const stackReplacements: string[] = [];
              const stackCount = getStackCount();
              const allStackIdentifiers = ["a", "b", "c", "d", "e"];
              const stackIdentifiers = allStackIdentifiers.slice(0, stackCount);

              for (const identifier of stackIdentifiers) {
                const group = value[`stack_group_${identifier}`] || {};
                const removed_serial_number =
                  group[`removed_serial_number_${identifier}`] || "";
                const added_serial_number =
                  group[`added_serial_number_${identifier}`] || "";
                const stack_symptom =
                  group[`stack_symptom_${identifier}`] || "";
                const stack_symptom_confirmed = group[
                  `stack_symptom_confirmed_${identifier}`
                ]
                  ? "true"
                  : "false";

                if (removed_serial_number || added_serial_number) {
                  stackReplacements.push(
                    `('${identifier}','${removed_serial_number}','${added_serial_number}','${stack_symptom}','${stack_symptom_confirmed}')`
                  );
                }
              }

              if (stackReplacements.length === 0) {
                await context.openAlertDialog({
                  title: "Validation Error",
                  message: "At least one stack replacement must be filled in.",
                });
                continue; // Stay in this step
              }

              updatedNote.stack_replacements = stackReplacements.join(",");
              break;

            case "Stack inspection":
              const stackInspections: string[] = [];
              const stackCount2 = getStackCount();
              const allStackIdentifiers2 = ["a", "b", "c", "d", "e"];
              const stackIdentifiers2 = allStackIdentifiers2.slice(
                0,
                stackCount2
              );

              for (const identifier of stackIdentifiers2) {
                const group =
                  value[`stack_group_inspection_${identifier}`] || {};
                const stack_identifier_value =
                  group[`stack_identifier_${identifier}`] || "";
                const stack_serial_number =
                  group[`stack_serial_number_${identifier}`] || "";
                const insight = group[`insight_${identifier}`] || "";

                if (stack_identifier_value || stack_serial_number || insight) {
                  stackInspections.push(
                    `('${identifier}','${stack_identifier_value}','${stack_serial_number}','${insight}')`
                  );
                }
              }

              if (stackInspections.length === 0) {
                await context.openAlertDialog({
                  title: "Validation Error",
                  message: "At least one stack inspection must be filled in.",
                });
                continue; // Stay in this step
              }

              updatedNote.stack_inspections = stackInspections.join(",");
              break;
          }

          // Save the recategorized note
          await notesService.edit(note._id, updatedNote);
          step = "exit";
        } else {
          step = "select_category";
        }
      }
    }
  }
  function handleSearchButtonClick(): void {
    searchInputVisible = true;
    tick().then(() => {
      searchInput?.focus();
    });
  }

  function handleSearchInputBlur(): void {
    if (!$filter.searchQuery) {
      searchInputVisible = false;
    }
  }

  function handleSearchInputClearClick(): void {
    $filter.searchQuery = null;
    searchInput?.blur();
    searchInputVisible = false;
  }

  function mapNoteToWhenDateTime(note: Note): string {
    return _mapNoteToFormattedDateTime(note);
  }

  function mapNoteToNeeded(note: Note): string {
    const date = DateTime.fromMillis(note.created_on, {
      locale: context.appData.locale,
      zone: context.appData.timeZone,
    });
    return date.year === now.year
      ? _mapNoteToFormattedDateTime(
          note,
          {
            month: "short",
            day: "numeric",
          },
          date
        )
      : _mapNoteToFormattedDateTime(
          note,
          {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
          },
          date
        );
  }

  function _mapNoteToFormattedDateTime(
    note: Note,
    formatOpts: DateTimeFormatOptions = {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "numeric",
      minute: "numeric",
    },
    date: DateTime = DateTime.fromMillis(note.created_on, {
      locale: context.appData.locale,
      zone: context.appData.timeZone,
    })
  ): string {
    return date.toLocaleString(formatOpts);
  }

  function createTooltip(
    button: HTMLButtonElement,
    options: { message: string }
  ): void {
    context.createTooltip(button, {
      message: options.message,
    });
  }

  function createTooltipOnEllipsis(element: HTMLElement): void {
    const elementWidth = element.offsetWidth;
    const elementContentWidth = element.scrollWidth;

    if (elementContentWidth > elementWidth) {
      context.createTooltip(element, {
        message: element.innerText,
      });
    }
  }

  function getCategory(id: number | null): ServiceLogbookCategory | null {
    return id !== null ? (categories.get(id) ?? null) : null;
  }

  function getNoteHtmlContent(note: NoteWithHtml): string {
    const subject = note.subject ? `<h2>${note.subject}</h2>` : "";
    const sanitizedHtml = context.sanitizeHtml(note.html, {
      allowStyleAttr: true,
    });
    // Category section
    const categoryName = note.note_category || "Uncategorized";
    const categorySection = `
    <div style="margin-bottom: 16px; padding: 8px; background-color: color-mix(in srgb, transparent, currentcolor 8%); border-radius: 4px;">
      <strong style="color: color-mix(in srgb, transparent, currentcolor 40%);">Category:</strong> 
      <span style="font-weight: 500;">${categoryName}</span>
    </div>
  `;

    // FIX: Universal check and display for 'Performed On'
    let performedOnHtml = "";
    if (note.performed_on) {
      const performedDate = DateTime.fromMillis(
        note.performed_on
      ).toLocaleString({
        year: "numeric",
        month: "long",
        day: "numeric",
      });
      performedOnHtml = `
          <div style="margin-bottom: 16px; padding: 8px; border-left: 3px solid color-mix(in srgb, transparent, currentcolor 20%);">
            <div style="margin-bottom: 8px;">
              <strong style="color: color-mix(in srgb, transparent, currentcolor 40%);">Performed On:</strong>
              <span>${performedDate}</span>
            </div>
          </div>
        `;
    }

    // Build category-specific fields section
    let categoryFields = "";
    switch (note.note_category) {
      case "Calibration":
        categoryFields = `
    <div style="margin-bottom: 16px; padding: 8px; border-left: 3px solid color-mix(in srgb, transparent, currentcolor 20%);">
      <div style="margin-bottom: 8px;">
        <strong style="color: color-mix(in srgb, transparent, currentcolor 40%);">Tag Numbers:</strong>
        <span>${note.tag_numbers?.join(", ") || "-"}</span>
      </div>
    </div>
  `;
        break;
      case "Settings change":
        categoryFields = `
    <div style="margin-bottom: 16px; padding: 8px; border-left: 3px solid color-mix(in srgb, transparent, currentcolor 20%);">
      <div style="margin-bottom: 8px;">
        <strong style="color: color-mix(in srgb, transparent, currentcolor 40%);">Tag Numbers:</strong>
        <span>${note.tag_numbers?.join(", ") || "-"}</span>
      </div>
    </div>
  `;
        break;
      case "Software update":
        categoryFields = `
    <div style="margin-bottom: 16px; padding: 8px; border-left: 3px solid color-mix(in srgb, transparent, currentcolor 20%);">
      ${
        note.software_type
          ? `<div style="margin-bottom: 8px;">
        <strong style="color: color-mix(in srgb, transparent, currentcolor 40%);">Software Type:</strong>
        <span>${note.software_type}</span>
      </div>`
          : ""
      }
      <div style="margin-bottom: 8px;">
        <strong style="color: color-mix(in srgb, transparent, currentcolor 40%);">Version:</strong>
        <span>${note.version || "-"}</span>
      </div>
    </div>
  `;
        break;
      case "Stack replacements":
        let stackHtml = "";

        // Removed the original 'if (note.performed_on)' block that was here

        if (note.stack_replacements) {
          const replacements = note.stack_replacements
            .split(";")
            .filter((r) => r.trim())
            .map((r) => {
              const match = r.match(
                /\('([^']+)','([^']*)','([^']*)','([^']*)','([^']+)'\)/
              );
              if (match) {
                return {
                  identifier: match[1],
                  removed: match[2],
                  added: match[3],
                  symptom: match[4],
                  confirmed: match[5] === "true",
                };
              }
              return null;
            })
            .filter((r) => r !== null);

          if (replacements.length > 0) {
            stackHtml += `<div style="margin-top: 12px;"><strong style="color: color-mix(in srgb, transparent, currentcolor 40%);">Stack Replacements:</strong></div>`;
            replacements.forEach((stack) => {
              const symptomLabel =
                {
                  high_crossover: "High crossover",
                  conductivity_issues: "Conductivity issues",
                  external_leak: "External leak",
                  internal_leak: "Internal leak",
                  ground_fault: "Ground fault",
                }[stack.symptom] ||
                stack.symptom ||
                "-";

              const confirmedBadge = stack.confirmed
                ? `<span style="display: inline-block; padding: 2px 6px; margin-left: 8px; background-color: #4caf50; color: white; border-radius: 3px; font-size: 10px; font-weight: 500;">✓ CONFIRMED</span>`
                : "";

              stackHtml += `
                <div style="margin: 8px 0; padding: 8px; background-color: color-mix(in srgb, transparent, currentcolor 4%); border-radius: 4px;">
                  <div style="font-weight: 500; margin-bottom: 4px;">
                    Stack ${stack.identifier.toUpperCase()}${confirmedBadge}
                  </div>
                  <div style="font-size: 11px; color: color-mix(in srgb, transparent, currentcolor 30%);">
                    <div>Removed: ${stack.removed || "-"}</div>
                    <div>Added: ${stack.added || "-"}</div>
                    <div>Symptom: ${symptomLabel}</div>
                  </div>
                </div>
              `;
            });
          }
        }

        categoryFields = `
        <div style="margin-bottom: 16px; padding: 8px; border-left: 3px solid color-mix(in srgb, transparent, currentcolor 20%);">
          ${stackHtml}
        </div>
      `;
        break;
      case "Stack inspection":
        let inspectionHtml = "";
        if (note.stack_inspections) {
          const inspections = note.stack_inspections
            .split(";")
            .filter((r) => r.trim())
            .map((r) => {
              const match = r.match(
                /\('([^']+)','([^']*)','([^']*)','([^']*)'\)/
              );
              if (match) {
                return {
                  identifier: match[1],
                  stack_identifier: match[2],
                  serial_number: match[3],
                  insight: match[4],
                };
              }
              return null;
            })
            .filter((r) => r !== null);

          if (inspections.length > 0) {
            inspectionHtml += `<div style="margin-top: 12px;"><strong style="color: color-mix(in srgb, transparent, currentcolor 40%);">Stack Inspections:</strong></div>`;
            inspections.forEach((inspection) => {
              inspectionHtml += `
          <div style="margin: 8px 0; padding: 8px; background-color: color-mix(in srgb, transparent, currentcolor 4%); border-radius: 4px;">
            <div style="font-weight: 500; margin-bottom: 4px;">
              Stack ${inspection.identifier.toUpperCase()}
            </div>
            <div style="font-size: 11px; color: color-mix(in srgb, transparent, currentcolor 30%);">
              <div>Stack Identifier: ${inspection.stack_identifier || "-"}</div>
              <div>Serial Number: ${inspection.serial_number || "-"}</div>
              <div>Insight: ${inspection.insight || "-"}</div>
            </div>
          </div>
        `;
            });
          }
        }

        categoryFields = `
    <div style="margin-bottom: 16px; padding: 8px; border-left: 3px solid color-mix(in srgb, transparent, currentcolor 20%);">
      ${inspectionHtml}
    </div>
  `;
        break;
    }

    // External note badge
    const externalNoteBadge = note.external_note
      ? `<div style="margin-bottom: 16px;">
         <span style="display: inline-block; padding: 4px 8px; background-color: #2196F3; color: white; border-radius: 4px; font-size: 11px; font-weight: 500;">
           📋 EXTERNAL NOTE
         </span>
       </div>`
      : "";
    return `
    <div class="card">
      <div class="card-header">
        <div class="note-info who">${_getNoteInfoWho(note)}</div>
        <div class="note-info when-what">${_getNoteInfoWhenWhat(note)}</div>
        <button class="icon-button more" data-testid="service-logbook-preview-more-button">
          <svg height="20px" viewBox="0 0 24 24" width="20px">
            <path d="M0 0h24v24H0V0z" fill="none" />
            <path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/>
          </svg>
        </button>
      </div>
      <div class="card-content">
        ${subject}
        ${externalNoteBadge}
        ${categorySection}
        ${performedOnHtml}
        ${categoryFields}
        <div style="margin-top: 16px;">
          ${sanitizedHtml}
        </div>
      </div>
    </div>`;
  }

  async function handleOpenCategorySelect(event: MouseEvent): Promise<void> {
    const target = event.target as HTMLElement;
    const selectTarget =
      (target.closest(".select-button") as HTMLElement) ?? target;

    const selectOptions = Array.from(categories.entries()).map(
      ([key, category]) => ({
        text: category.name,
        key,
      })
    );
    const selected = $filter.selectedCategoryId
      ? selectOptions.findIndex(
          (option) => option.key === $filter.selectedCategoryId
        )
      : undefined;

    const options: SingleSelectPanelOptions = {
      options: selectOptions,
      selected,
    };
    const result = await context.openSelectPanel(selectTarget, options);
    if (result) {
      const selectedCategoryId = selectOptions[result.index].key;
      $filter.selectedCategoryId = selectedCategoryId;
    }
  }

  function updateNoteHtmlContent(root: ShadowRoot, note: NoteWithHtml): void {
    const noteInfoWho = root.querySelector(".note-info.who");
    const noteInfoWhenWhat = root.querySelector(".note-info.when-what");
    const cardContent = root.querySelector(".card-content");

    if (noteInfoWho) {
      noteInfoWho.innerHTML = _getNoteInfoWho(note);
    }
    if (noteInfoWhenWhat) {
      noteInfoWhenWhat.innerHTML = _getNoteInfoWhenWhat(note);
    }
    if (cardContent) {
      // Reconstruct the entire content with all fields
      const subject = note.subject ? `<h2>${note.subject}</h2>` : "";
      const sanitizedHtml =
        context.sanitizeHtml(note.html, { allowStyleAttr: true }) ?? "";

      // Reuse the logic from getNoteHtmlContent for consistency
      // Extract just the content part (everything inside card-content)
      const fullHtml = getNoteHtmlContent(note);
      const contentMatch = fullHtml.match(
        /<div class="card-content">([\s\S]*)<\/div>\s*<\/div>$/
      );
      if (contentMatch) {
        cardContent.innerHTML = contentMatch[1];
      }
    }
  }

  function _getNoteInputs(category: string, isEdit = false): ComponentInput[] {
    const inputs: ComponentInput[] = [];
    inputs.push({
      key: "performed_on",
      type: "Date",
      label: "Performed on",
      required: true,
    });
    // Add category-specific fields
    switch (category) {
      case "Calibration":
        inputs.push({
          key: "tag_numbers",
          type: "List" as const,
          label: "Tag Numbers",
          required: true,
          itemType: {
            key: "tag_number",
            type: "String",
            label: "Tag Number",
            placeholder: "Enter tag number",
          },
        });
        break;

      case "Stack replacements":
        inputs.push({
          key: "workorder_id",
          type: "String",
          label: "Workorder ID",
          required: false,
          placeholder: "Enter the workorder ID if applicable e.g., (WO-002527)",
        });

        // Dynamically determine number of stacks based on agent type
        const stackCount = getStackCount();
        const allStackIdentifiers = ["a", "b", "c", "d", "e"];
        const stackIdentifiers = allStackIdentifiers.slice(0, stackCount);

        for (const identifier of stackIdentifiers) {
          inputs.push({
            key: `stack_group_${identifier}`,
            type: "Group" as const,
            label: `Stack Location ${identifier.toUpperCase()}`,
            children: [
              {
                key: `stack_identifier_${identifier}`,
                type: "String",
                label: "Identifier",
                defaultValue: `Stack ${identifier.toUpperCase()}`,
                disabled: true,
              },
              {
                key: `removed_serial_number_${identifier}`,
                type: "String",
                label: "Removed Serial",
                required: false,
                placeholder: "Enter removed serial",
              },
              {
                key: `added_serial_number_${identifier}`,
                type: "String",
                label: "Added Serial",
                required: false,
                placeholder: "Enter added serial",
              },
              {
                key: `stack_symptom_${identifier}`,
                type: "Selection" as const,
                label: "Stack Symptom",
                required: false,
                options: [
                  { label: "None", value: null },
                  { label: "High crossover", value: "high_crossover" },
                  {
                    label: "Conductivity issues",
                    value: "conductivity_issues",
                  },
                  { label: "External leak", value: "external_leak" },
                  { label: "Internal leak", value: "internal_leak" },
                  { label: "Tie Rod", value: "tie_rod" },
                  {
                    label:
                      "Other (please specify the symptom in the text field below)",
                    value: "Other",
                  },
                ],
              },
              {
                key: `stack_symptom_confirmed_${identifier}`,
                type: "Checkbox" as const,
                label: "Stack Symptom Confirmed",
                defaultValue: false,
              },
            ],
          });
        }
        break;
      case "Stack inspection":
        // Dynamically determine number of stacks based on agent type
        const stackCountInspection = getStackCount();
        const allStackIdentifiersInspection = ["a", "b", "c", "d", "e"];
        const stackIdentifiersInspection = allStackIdentifiersInspection.slice(
          0,
          stackCountInspection
        );

        for (const identifier of stackIdentifiersInspection) {
          inputs.push({
            key: `stack_group_inspection_${identifier}`,
            type: "Group" as const,
            label: `Stack ${identifier.toUpperCase()}`,
            required: false,
            children: [
              {
                key: `stack_identifier_${identifier}`,
                type: "String",
                label: "Stack Identifier",
                placeholder: "e.g., Stack A",
                required: false,
                defaultValue: `Stack ${identifier.toUpperCase()}`,
                disabled: true,
              },
              {
                key: `stack_serial_number_${identifier}`,
                type: "String",
                label: "Stack Serial Number",
                placeholder: "Enter serial number",
                required: false,
              },
              {
                key: `insight_${identifier}`,
                type: "String",
                label: "Insight",
                placeholder: "Enter insight",
                required: false,
              },
            ],
          });
        }
        break;
      case "Settings change":
        inputs.push({
          key: "tag_numbers",
          type: "List" as const,
          label: "Tag Numbers",
          required: true,
          itemType: {
            key: "tag_number",
            type: "String",
            label: "Tag Number",
            placeholder: "Enter tag number",
          },
        });
        break;

      case "Software update":
        inputs.push(
          {
            key: "software_type",
            type: "Selection" as const,
            label: "Software Type",
            required: true,
            options: [
              { label: "PLC software", value: "PLC software" },
              { label: "Ixon router", value: "Ixon router" },
              { label: "HMI software", value: "HMI software" },
              {
                label:
                  "Other (please specify the updated software in the text field below)",
                value: "Other",
              },
            ],
          },
          {
            key: "version",
            type: "String",
            label: "Software Version",
            required: false,
            placeholder: "Enter new software version (e.g., v2.1.0)",
          }
        );
        break;
      default:
        // No unique fields for other categories
        break;
    }

    // Add common fields for ALL categories
    inputs.push(
      {
        key: "text",
        type: "RichText" as const,
        label: "Description of event",
        placeholder: "Description of event",
        required: false,
        translate: false,
        description:
          category === "Stack replacements"
            ? "---\n**Required**"
            : "**Required**",
      },
      {
        key: "external_note",
        type: "Checkbox" as const,
        label: "External Note",
        defaultValue: false,
        description:
          "Mark this note as external if it can be viewed by parties outside the company (e.g., external partners or customers)",
      }
    );

    return inputs;
  }

  function _getCategoryInput(): ComponentInput {
    const options =
      [...(categories?.values() ?? [])].map((category) => ({
        label: category.name,
        value: category.id,
      })) ?? [];
    const categoryInput = {
      key: "category",
      type: "Selection" as const,
      label: translations.CATEGORY,
      required: false,
      options: [
        {
          label: translations.NONE,
        },
        ...options,
      ] as ComponentInput["options"],
    };

    return categoryInput;
  }

  function _getNoteInfoWho(note: NoteWithHtml) {
    const userName = getNoteUserName(usersDict, note);
    const { width, height, backgroundColor } = getStyle(userName, 22);
    const editedBy =
      note.editor_id && note.editor_name
        ? (() => {
            const editedByUser = getNoteEditedBy(usersDict, note);
            const editedDate = note.updated_on
              ? DateTime.fromMillis(note.updated_on).toLocaleString(
                  DateTime.DATETIME_SHORT
                )
              : "";
            const dateText = editedDate ? ` on ${editedDate}` : "";
            return `<span class="edited-by"><i>${context.translate("EDITED_BY_USER", { user: editedByUser })}${dateText}</i></span>`;
          })()
        : "";
    return `<svg class="user-avatar" style="background-color:${backgroundColor}; width:${width}; height: ${height};"><text x="50%" y="50%" text-anchor="middle" dominant-baseline="central">${getFirstLetter(userName)}</text></svg><span><span class="name">${userName}</span>${editedBy}</span>`;
  }

  function _getNoteInfoWhenWhat(note: NoteWithHtml): string {
    if (note.category !== null) {
      const category = getCategory(note.category);
      const categoryLabel = category
        ? `<span class="category" style="${getCategoryStyle(category)}">${category.name}</span>`
        : "";
      return `<span>${mapNoteToWhenDateTime(note)}</span>${categoryLabel}`;
    }
    return `<span>${mapNoteToWhenDateTime(note)}</span>`;
  }

  function getNoteCategoryName(note: Note): string {
    if (note.note_category) {
      return note.note_category;
    }
    const category = getCategory(note.category);
    if (category) {
      return category.name;
    }
    return translations.UNCATEGORIZED || "Uncategorized";
  }
  async function handleDownloadJsonButtonClick(): Promise<void> {
    const result = await notesService.exportData();
    if (result.data.success) {
      const data = new Blob([JSON.stringify(result.data.data, null, 2)], {
        type: "application/json",
      });
      const fileName = `${kebabCase(
        deburr(agentOrAssetName ?? undefined)
      )}_service-logbook-notes.json`;
      if ("saveAsFile" in context) {
        context.saveAsFile(data, fileName);
      }
    }
  }

  // CORRECTED: handleUploadJsonButtonClick function for service-logbook.svelte
  // Replace your existing handleUploadJsonButtonClick function with this code

  async function handleUploadJsonButtonClick(): Promise<void> {
    const result = await context.openFormDialog({
      title: translations.IMPORT_FROM_JSON,
      inputs: [
        {
          key: "file",
          type: "File",
          label: "JSON File",
          accept: ".json",
          required: true,
        },
      ],
      submitButtonText: translations.IMPORT,
    });

    if (result && result.value && result.value.file) {
      const file = result.value.file;
      const reader = new FileReader();
      reader.onload = async (event) => {
        if (event.target && event.target.result) {
          try {
            const parsedData = JSON.parse(event.target.result as string);

            // FIX: Extract the notes array from the JSON structure
            // The export format includes metadata (exported_on, exported_by, etc.)
            // so we need to extract just the notes array
            const notesArray = Array.isArray(parsedData)
              ? parsedData
              : parsedData.notes;

            // Validate that we actually have a notes array
            if (!notesArray || !Array.isArray(notesArray)) {
              context.openAlertDialog({
                title: "Error",
                message:
                  "Invalid JSON file format. Expected a 'notes' array or an array of note objects.",
              });
              return;
            }

            // Check if the array is empty
            if (notesArray.length === 0) {
              context.openAlertDialog({
                title: "Warning",
                message: "The JSON file contains no notes to import.",
              });
              return;
            }

            // Confirm with user before importing
            const confirmed = await context.openConfirmDialog({
              title: translations.IMPORT,
              message: translations["__TEXT__.CONFIRM_IMPORT"],
              confirmButtonText: translations.IMPORT,
              destructive: true,
            });

            if (confirmed) {
              // FIX: Pass ONLY the notes array, not the entire export object
              await notesService.importData(notesArray);
              await notesService.load();
            }
          } catch (error) {
            console.error("Import error:", error);
            context.openAlertDialog({
              title: "Error",
              message:
                "Invalid JSON file. Please ensure the file is a valid JSON export from the Service Logbook.",
            });
          }
        }
      };
      reader.readAsText(file);
    }
  }
</script>

<div class="card" bind:this={rootEl} class:is-narrow={isNarrow}>
  <div class="card-header">
    <h3 class="card-title" data-testid="service-logbook-card-title">
      {translations.SERVICE_LOGBOOK}
    </h3>
    <div class="card-header-actions">
      {#if searchInputVisible}
        <div class="search-input-container">
          <div class="search-input-prefix">
            <svg width="24" height="24" viewBox="0 0 24 24">
              <path d="M0 0h24v24H0z" fill="none" />
              <path
                d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3
              9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6
              0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"
              />
            </svg>
          </div>
          <input
            type="text"
            class="search-input"
            bind:this={searchInput}
            bind:value={$filter.searchQuery}
            on:blur={handleSearchInputBlur}
            placeholder={translations.SEARCH}
            data-testid="service-logbook-search-input"
          />
          <div class="search-input-suffix">
            <button
              class="icon-button"
              on:click={handleSearchInputClearClick}
              data-testid="service-logbook-search-clear-button"
            >
              <svg width="20" height="20" viewBox="0 0 24 24">
                <path d="M0 0h24v24H0z" fill="none" />
                <path
                  d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59
                19 19 17.59 13.41 12z"
                />
              </svg>
            </button>
          </div>
        </div>
      {/if}

      {#if !!$notes?.length}
        {#if !isSmall && categories.size > 0 && !searchInputVisible}
          <div
            class="filter-select"
            data-testid="service-logbook-category-filter"
          >
            <button
              class="select-button"
              data-testid="service-logbook-category-select-button"
              on:click={handleOpenCategorySelect}
            >
              <span>{$selectedCategoryName}</span>
              <svg fill="currentcolor" height="18" viewBox="0 0 24 24">
                <path d="M7 10l5 5 5-5z" />
                <path d="M0 0h24v24H0z" fill="none" />
              </svg>
            </button>
            {#if $filter.selectedCategoryId !== null}
              <button
                class="icon-button"
                data-testid="service-logbook-category-clear-button"
                on:click={() =>
                  filter.update((f) => ({ ...f, selectedCategoryId: null }))}
              >
                <svg width="24" height="24" viewBox="0 0 24 24">
                  <path d="M0 0h24v24H0z" fill="none" />
                  <path
                    d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
                  />
                </svg>
              </button>
            {/if}
          </div>
        {/if}

        <button
          use:createTooltip={{ message: translations.SEARCH }}
          class="icon-button"
          class:hidden={searchInputVisible}
          data-testid="service-logbook-search-button"
          on:click={handleSearchButtonClick}
        >
          <svg
            enable-background="new 0 0 24 24"
            height="24px"
            viewBox="0 -960 960 960"
            width="24px"
            fill="#000000"
            ><path
              d="M784-120 532-372q-30 24-69 38t-83 14q-109 0-184.5-75.5T120-580q0-109 75.5-184.5T380-840q109 0 184.5 75.5T640-580q0 44-14 83t-38 69l252 252-56 56ZM380-400q75 0 127.5-52.5T560-580q0-75-52.5-127.5T380-760q-75 0-127.5 52.5T200-580q0 75 52.5 127.5T380-400Z"
            />
          </svg>
        </button>
        <button
          use:createTooltip={{ message: translations.EXPORT_TO_CSV }}
          class="icon-button"
          class:hidden={searchInputVisible}
          data-testid="service-logbook-export-button"
          on:click={() => handleDownloadCsvButtonClick($filteredNotesWithHtml)}
        >
          <svg
            enable-background="new 0 0 24 24"
            height="24px"
            viewBox="0 -960 960 960"
            width="24px"
            fill="#000000"
            ><path
              d="M480-320 280-520l56-58 104 104v-326h80v326l104-104 56 58-200 200ZM240-160q-33 0-56.5-23.5T160-240v-120h80v120h480v-120h80v120q0 33-23.5 56.5T720-160H240Z"
            />
          </svg>
        </button>
        <!-- <button
          use:createTooltip={{ message: translations.EXPORT_TO_JSON }}
          class="icon-button"
          class:hidden={searchInputVisible}
          data-testid="service-logbook-export-json-button"
          on:click={handleDownloadJsonButtonClick}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            height="24px"
            viewBox="0 0 24 24"
            width="24px"
            fill="#000000"
          >
            <path d="M0 0h24v24H0z" fill="none" />
            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
          </svg>
        </button> -->
        <!-- <button
          use:createTooltip={{ message: translations.IMPORT_FROM_JSON }}
          class="icon-button"
          class:hidden={searchInputVisible}
          data-testid="service-logbook-import-json-button"
          on:click={handleUploadJsonButtonClick}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            height="24px"
            viewBox="0 0 24 24"
            width="24px"
            fill="#000000"
          >
            <path d="M0 0h24v24H0z" fill="none" />
            <path
              d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"
            />
          </svg>
        </button> -->
      {/if}

      <button
        bind:this={addButton}
        class="icon-button"
        class:hidden={searchInputVisible}
        data-testid="service-logbook-add-button"
        on:click={handleAddButtonClick}
      >
        <svg
          enable-background="new 0 0 24 24"
          height="24px"
          viewBox="0 -960 960 960"
          width="24px"
          fill="#000000"
          ><path
            d="M440-240h80v-120h120v-80H520v-120h-80v120H320v80h120v120ZM240-80q-33 0-56.5-23.5T160-160v-640q0-33 23.5-56.5T240-880h320l240 240v480q0 33-23.5 56.5T720-80H240Zm280-520v-200H240v640h480v-440H520ZM240-800v200-200 640-640Z"
          />
        </svg>
      </button>
    </div>
  </div>
  {#if isSmall && !!$notes?.length && categories.size > 0}
    <div class="card-chips">
      <div class="filter-select" data-testid="service-logbook-category-filter">
        <button
          class="select-button"
          data-testid="service-logbook-category-select-button"
          on:click={handleOpenCategorySelect}
        >
          <span>{$selectedCategoryName}</span>
          <svg fill="currentcolor" height="18" viewBox="0 0 24 24">
            <path d="M7 10l5 5 5-5z" />
            <path d="M0 0h24v24H0z" fill="none" />
          </svg>
        </button>
        {#if $filter.selectedCategoryId !== null}
          <button
            class="icon-button"
            data-testid="service-logbook-category-clear-button"
            on:click={() =>
              filter.update((f) => ({ ...f, selectedCategoryId: null }))}
          >
            <svg width="24" height="24" viewBox="0 0 24 24">
              <path d="M0 0h24v24H0z" fill="none" />
              <path
                d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
              />
            </svg>
          </button>
        {/if}
      </div>
    </div>
  {/if}
  <div class="card-content">
    {#if !!$loaded}
      {#if !!$filteredNotesWithHtml?.length}
        <div class="list-wrapper">
          <div class="base-list">
            {#each $filteredNotesWithHtml as note, index}
              <div
                class="list-item note-clickable"
                data-testid="service-logbook-list-item"
              >
                <div
                  class="list-item-content"
                  class:is-narrow={isNarrow}
                  on:click={() => handlePreviewNoteClick(note)}
                  on:keyup={() => handlePreviewNoteClick(note)}
                  role="button"
                  tabindex="0"
                >
                  <div
                    class="list-item-flex-container"
                    class:is-narrow={isNarrow}
                  >
                    <span class="name">{getNoteUserName(usersDict, note)}</span>
                    {#if $notesWithCategories}
                      <span
                        use:createTooltipOnEllipsis
                        class="category"
                        style={getCategoryStyle(getCategory(note.category))}
                        >{getCategory(note.category)?.name ?? ""}
                      </span>
                    {/if}
                    <span
                      use:createTooltipOnEllipsis
                      class="category"
                      style={getCategoryStyle(getCategory(note.category))}
                      >{getNoteCategoryName(note)}
                    </span>
                    <span class="text">
                      {#if note.subject}
                        <strong>{note.subject}</strong>
                        <span> – </span>
                      {/if}{HtmlToReadableText(note.html)}
                    </span>
                  </div>

                  <div
                    class="list-item-flex-container"
                    class:is-narrow={isNarrow}
                  >
                    <span class="date">{mapNoteToNeeded(note)}</span>
                    <button
                      class="icon-button more"
                      use:createTooltip={{ message: translations.MORE_OPTIONS }}
                      on:click={(event) =>
                        handleMoreActionsButtonClick(event, note)}
                      data-testid="service-logbook-list-item-more-button"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        height="24px"
                        viewBox="0 0 24 24"
                        width="24px"
                        ><path d="M0 0h24v24H0V0z" fill="none" /><path
                          d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"
                        /></svg
                      >
                    </button>
                  </div>
                </div>
              </div>
            {/each}
          </div>
        </div>
      {:else}
        <div class="empty-state" data-testid="service-logbook-empty-state">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"
            ><g
              ><rect x="4" y="15" width="10" height="2" /><polygon
                points="9.003,9 7.004,7 4,7 4,9"
              /><polygon points="11.001,11 4,11 4,13 13,13" /><polygon
                points="20,11 13.546,11 15.546,13 20,13"
              /><polygon points="11.546,9 20,9 20,7 9.546,7" /></g
            ><path d="M19.743,22.289l1.27-1.27L2.95,2.956l-1.27,1.28" /></svg
          >
          {#if $filter.searchQuery || $filter.selectedCategoryId}
            <p>{translations["__TEXT__.NO_MATCHING_RESULTS"]}</p>
          {:else}
            <p>{translations.NO_NOTES}</p>
          {/if}
        </div>
      {/if}
    {:else}
      <div class="loading-state">
        <div class="spinner">
          <svg
            preserveAspectRatio="xMidYMid meet"
            focusable="false"
            viewBox="0 0 100 100"
          >
            <circle cx="50%" cy="50%" r="45" />
          </svg>
        </div>
      </div>
    {/if}
  </div>
</div>

<style lang="scss">
  @use "./styles/button" as *;
  @use "./styles/card" as *;
  @use "./styles/list" as *;
  @use "./styles/spinner" as *;

  @use "./styles/select" as *;

  .hidden {
    visibility: hidden;
  }

  .search-input-container {
    display: flex;
    flex-direction: row;
    height: 40px;
    margin-left: 8px;
    border-radius: 20px;
    background-color: color-mix(in srgb, transparent, currentcolor 4%);

    input {
      background-color: transparent;
      height: 32px;
      width: 140px;
      padding: 4px 8px 4px 0;
      margin: 0;
      border: none;
      outline: none;
      line-height: 24px;
      font-size: 14px;
      color: currentcolor;
    }

    .search-input-prefix {
      width: 24px;
      height: 24px;
      padding: 8px;
      fill: currentcolor;
    }

    .search-input-suffix {
      width: 40px;
      height: 40px;

      .icon-button {
        background-color: transparent;

        svg {
          height: 20px;
          width: 20px;
          margin: 10px;
          line-height: 20px;
        }
      }
    }
  }

  .card {
    .card-header {
      display: flex;
      flex-direction: row;
      height: 40px;

      .card-title {
        flex: 1 0 auto;
      }
    }

    &:not(.is-narrow) {
      .card-header {
        height: 52px;
      }

      .card-header-actions {
        padding: 8px;

        @media print {
          display: none;
        }
      }
    }
  }

  .card-header .button {
    display: flex;
    flex-direction: row;
    align-items: center;
    padding-right: 12px;
    padding-left: 8px;
    background-color: var(--accent);
    line-height: 32px;
    font-size: 14px;
    color: var(--accent-color);

    svg {
      margin-right: 4px;
      fill: var(--accent-color);
    }
  }

  .card-chips {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 8px;
    padding: 8px;
    margin-bottom: 8px;
  }

  .card-content {
    position: relative;
    z-index: 1;
  }

  .card-content {
    .list-wrapper {
      position: absolute;
      left: 0;
      right: 0;
      top: 0;
      bottom: 0;
      padding: 0 8px;
      overflow: auto;
      overflow-anchor: none;

      .note-clickable {
        cursor: pointer;

        &:hover {
          background-color: color-mix(in srgb, transparent, currentcolor 12%);
        }
      }

      .list-item {
        padding: 0 8px;
        margin: 0 -8px;

        .list-item-content {
          width: 100%;

          &.is-narrow {
            align-items: flex-start;
          }

          .list-item-flex-container {
            display: flex;
            flex-direction: row;
            align-items: center;

            &.is-narrow {
              flex-direction: column;
              padding-top: 8px;
              align-items: baseline;

              &:first-of-type {
                gap: 8px;
              }

              &:last-of-type {
                align-items: end;
              }
            }

            &:first-of-type {
              flex: 1;
              min-width: 0; /* or some value */
              margin-right: 8px;
            }

            &:last-of-type {
              margin-left: auto;
            }

            .icon-button {
              margin-right: -8px;
            }
          }

          .name {
            min-width: 160px;
            width: 160px;
            overflow-wrap: break-word;
          }

          .category {
            padding: 4px 8px;
            margin-right: 8px;
            border-radius: 4px;
            min-width: 100px;
            width: 100px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            text-align: center;
          }

          .text {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }

          .is-narrow .text {
            display: -webkit-box;
            white-space: normal;
            width: 100%;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
          }
        }
      }
    }
  }

  .col:hover .col-actions {
    display: flex;
  }

  .empty-state,
  .loading-state {
    display: flex;
    height: 100%;
    flex-direction: column;
    place-content: center;
    align-items: center;
  }

  .empty-state {
    font-size: 12px;
    color: color-mix(in srgb, currentcolor 54%, transparent);

    p {
      width: 100%;
      margin: 8px 0;
      text-align: center;
    }
  }
</style>
