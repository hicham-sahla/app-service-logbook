<script lang="ts">
  import { onMount } from 'svelte';
  import type { Writable } from 'svelte/store';
  import type { ComponentContext, ResourceData } from '@ixon-cdk/types';
  import type { Note } from './types';
  import { NotesService } from './notes.service';
  import { DateTime, type DateTimeFormatOptions } from 'luxon';

  export let context: ComponentContext;

  let rootEl: HTMLDivElement;
  let agentOrAsset: ResourceData.Agent | ResourceData.Asset | null = null;
  let myUser: ResourceData.MyUser | null = null;
  let loaded: Writable<boolean>;
  let notes: Writable<Note[]>;
  let notesService: NotesService;
  let translations: { [key: string]: string } = {};
  let usersDict: Record<string, ResourceData.User> | null = null;
  let width: number | null = null;

  $: isNarrow = width !== null ? width <= 460 : false;

  onMount(async () => {
    translations = context.translate([
      'ADD_NOTE',
      'NO_NOTES',
      'NOTE',
      'SERVICE_LOGBOOK',
      'WHEN',
      'WHO',
    ]);

    const backendComponentClient = context.createBackendComponentClient();
    notesService = new NotesService(backendComponentClient);
    loaded = notesService.loaded;
    notes = notesService.notes;
    notesService.load();

    const resourceDataClient = context.createResourceDataClient();
    resourceDataClient.query(
      [
        { selector: 'Agent', fields: ['permissions', 'publicId'] },
        { selector: 'Asset', fields: ['permissions', 'publicId'] },
      ],
      ([agentResult, assetResult]) => {
        agentOrAsset = agentResult.data ?? assetResult.data;
      },
    );
    resourceDataClient.query(
      [
        { selector: 'MyUser', fields: ['publicId', 'support'] },
        { selector: 'UserList', fields: ['name', 'publicId'] },
      ],
      ([myUserResult, userListResult]) => {
        myUser = myUserResult.data;
        if (userListResult.data) {
          usersDict = userListResult.data.reduce(
            (dict, user) => ({ ...dict, [user.publicId]: user }),
            {},
          );
        }
      },
    );

    width = rootEl.getBoundingClientRect().width;
    const resizeObserver = new ResizeObserver(entries => {
      entries.forEach(entry => {
        width = entry.contentRect.width;
      });
    });
    resizeObserver.observe(rootEl);

    return () => {
      resizeObserver.unobserve(rootEl);
    };
  });

  function getNoteIsActionable(
    _agentOrAsset: ResourceData.Agent | ResourceData.Asset | null,
    _myUser: ResourceData.MyUser | null,
    note: Note,
  ): boolean {
    // Company admin users are able to modify or delete any user’s notes.
    if (_agentOrAsset?.permissions?.includes('COMPANY_ADMIN')) {
      return true;
    }
    // Users with rights to manage this device are able to modify or delete any user’s notes.
    if (_agentOrAsset?.permissions?.includes('MANAGE_AGENT')) {
      return true;
    }
    // Support users are able to modify or delete any user’s notes.
    if (_myUser?.support) {
      return true;
    }
    // Users are able to modify or delete their own notes.
    return note.user === _myUser?.publicId;
  }

  function getNoteUserName(
    _usersDict: Record<string, ResourceData.User> | null,
    note: Note,
  ): string {
    return _usersDict
      ? _usersDict[note.user]?.name ?? context.translate('UNKNOWN_USER')
      : '';
  }

  async function handleAddButtonClick(): Promise<void> {
    const result = await context.openFormDialog({
      title: context.translate('ADD_NOTE'),
      inputs: [
        {
          key: 'text',
          type: 'Text',
          label: context.translate('NOTE'),
          required: true,
        },
      ],
      submitButtonText: context.translate('ADD'),
      discardChangesPrompt: true,
    });
    if (result && result.value) {
      const { text } = result.value;
      notesService.add(text);
    }
  }

  async function handleRemoveNoteButtonClick(note: Note): Promise<void> {
    const confirmed = await context.openConfirmDialog({
      title: context.translate('REMOVE_NOTE'),
      message: context.translate('__TEXT__.CONFIRM_NOTE_REMOVAL'),
      confirmButtonText: context.translate('REMOVE'),
      confirmCheckbox: true,
      destructive: true,
    });
    if (confirmed) {
      notesService.remove(note._id);
    }
  }

  async function handleMoreActionsButtonClick(note: Note): Promise<void> {
    const actions = [
      { title: context.translate('EDIT') },
      { title: context.translate('REMOVE'), destructive: true },
    ];
    const result = await context.openActionBottomSheet({ actions });
    if (result) {
      switch (result.index) {
        case 0:
          handleEditNoteButtonClick(note);
          break;
        case 1:
          handleRemoveNoteButtonClick(note);
          break;
      }
    }
  }

  async function handleEditNoteButtonClick(note: Note): Promise<void> {
    const result = await context.openFormDialog({
      title: context.translate('EDIT_NOTE'),
      inputs: [
        {
          key: 'text',
          type: 'Text',
          label: context.translate('NOTE'),
          required: true,
        },
      ],
      initialValue: { text: note.text },
      submitButtonText: context.translate('CONFIRM'),
      discardChangesPrompt: true,
    });
    if (result && result.value) {
      const { text } = result.value;
      await notesService.edit(note._id, text);
    }
  }

  function mapNoteToWhenDateTime(note: Note): string {
    return _mapNoteToFormattedDateTime(note);
  }

  function mapNoteToWhenDate(note: Note): string {
    return _mapNoteToFormattedDateTime(note, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  }

  function mapNoteToWhenTime(note: Note): string {
    return _mapNoteToFormattedDateTime(note, {
      hour: 'numeric',
      minute: 'numeric',
    });
  }

  function _mapNoteToFormattedDateTime(
    note: Note,
    formatOpts: DateTimeFormatOptions = {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
    },
  ): string {
    return DateTime.fromMillis(note.created_on, {
      locale: context.appData.locale,
      zone: context.appData.timeZone,
    }).toLocaleString(formatOpts);
  }
</script>

<div class="card" bind:this={rootEl} class:is-narrow={isNarrow}>
  <div class="card-header">
    <h3 class="card-title" data-testid="service-logbook-card-title">
      {translations.SERVICE_LOGBOOK}
    </h3>
    <div class="card-header-actions">
      {#if isNarrow}
        <button
          class="icon-button"
          data-testid="service-logbook-add-button"
          on:click={handleAddButtonClick}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            enable-background="new 0 0 24 24"
            height="24px"
            viewBox="0 0 24 24"
            width="24px"
            fill="#000000"
            ><g><rect fill="none" height="24" width="24" /></g><g
              ><g /><g
                ><path
                  d="M17,19.22H5V7h7V5H5C3.9,5,3,5.9,3,7v12c0,1.1,0.9,2,2,2h12c1.1,0,2-0.9,2-2v-7h-2V19.22z"
                /><path
                  d="M19,2h-2v3h-3c0.01,0.01,0,2,0,2h3v2.99c0.01,0.01,2,0,2,0V7h3V5h-3V2z"
                /><rect height="2" width="8" x="7" y="9" /><polygon
                  points="7,12 7,14 15,14 15,12 12,12"
                /><rect height="2" width="8" x="7" y="15" /></g
              ></g
            ></svg
          >
        </button>
      {:else}
        <button
          class="button"
          data-testid="service-logbook-add-button"
          on:click={handleAddButtonClick}
        >
          <svg height="24" viewBox="0 -960 960 960" width="24"
            ><path
              d="M450-200v-250H200v-60h250v-250h60v250h250v60H510v250h-60Z"
            /></svg
          >
          <span>{translations.ADD_NOTE}</span>
        </button>
      {/if}
    </div>
  </div>
  <div class="card-content">
    {#if !!$loaded}
      {#if !!$notes?.length}
        <div class="table-wrapper">
          <table class="table" class:sticky-column={!isNarrow}>
            <thead data-testid="service-logbook-table-head">
              <tr>
                {#if !isNarrow}
                  <th class="col">{translations.WHO}</th>
                {/if}
                <th class="col">
                  {#if isNarrow}
                    <span>{translations.WHO + ' / '}</span>
                  {/if}
                  <span>{translations.WHEN}</span>
                </th>
                <th class="col">{translations.NOTE}</th>
              </tr>
            </thead>
            <tbody>
              {#each $notes as note}
                <tr class="row" data-testid="service-logbook-table-row">
                  {#if !isNarrow}
                    <td class="col">
                      <span class="who">{getNoteUserName(usersDict, note)}</span
                      >
                    </td>
                  {/if}
                  <td class="col">
                    {#if isNarrow}
                      <div>
                        <div class="who">
                          {getNoteUserName(usersDict, note)}
                        </div>
                        <div class="when-date">
                          {mapNoteToWhenDate(note)}
                        </div>
                        <div class="when-time">
                          {mapNoteToWhenTime(note)}
                        </div>
                      </div>
                    {:else}
                      <div class="when">
                        {mapNoteToWhenDateTime(note)}
                      </div>
                    {/if}
                  </td>
                  <td class="col">
                    <div class="col-container">
                      <span>{note.text}</span>
                      {#if getNoteIsActionable(agentOrAsset, myUser, note)}
                        <div class="col-actions">
                          <button
                            class="icon-button"
                            data-testid="service-logbook-edit-button"
                            on:click={() => handleEditNoteButtonClick(note)}
                          >
                            <svg height="20px" viewBox="0 0 24 24" width="20px"
                              ><path d="M0 0h24v24H0V0z" fill="none" /><path
                                d="M14.06 9.02l.92.92L5.92 19H5v-.92l9.06-9.06M17.66 3c-.25 0-.51.1-.7.29l-1.83 1.83 3.75 3.75 1.83-1.83c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.2-.2-.45-.29-.71-.29zm-3.6 3.19L3 17.25V21h3.75L17.81 9.94l-3.75-3.75z"
                              /></svg
                            >
                          </button>
                          <button
                            class="icon-button"
                            data-testid="service-logbook-remove-button"
                            on:click={() => handleRemoveNoteButtonClick(note)}
                          >
                            <svg height="20px" viewBox="0 0 24 24" width="20px"
                              ><path d="M0 0h24v24H0V0z" fill="none" /><path
                                d="M16 9v10H8V9h8m-1.5-6h-5l-1 1H5v2h14V4h-3.5l-1-1zM18 7H6v12c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7z"
                              /></svg
                            >
                          </button>

                          <button
                            class="icon-button more"
                            on:click={() => handleMoreActionsButtonClick(note)}
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
                      {/if}
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
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
          <p>{translations.NO_NOTES}</p>
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
  @import './styles/button';
  @import './styles/card';
  @import './styles/spinner';

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

  .card-header .icon-button {
    color: var(--blue);
  }

  .card-header .button {
    display: flex;
    flex-direction: row;
    align-items: center;
    padding-right: 12px;
    padding-left: 8px;
    background-color: var(--blue);
    line-height: 32px;
    font-size: 14px;
    color: white;

    svg {
      margin-right: 4px;
      fill: white;
    }
  }

  .card-content {
    position: relative;
  }

  .table-wrapper {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    bottom: 0;
    padding: 0 8px;
    overflow: auto;
    overflow-anchor: none;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  table thead th {
    position: sticky;
    white-space: nowrap;
    background: var(--basic);
    top: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 7em;
    z-index: 10;
    text-align: left;
  }

  table thead tr {
    font-weight: 600;
  }

  table thead tr .col {
    padding: 0 6px 12px 0;
  }

  table thead tr,
  table tbody tr {
    height: 28px;

    .col:last-child {
      padding-right: 0;
    }
  }

  table tbody tr:hover {
    background-color: #f7f7f7;
  }

  table tbody tr .col {
    padding: 6px 6px 6px 0;
    line-height: 16px;
    border-bottom: 1px solid var(--card-border-color);
    vertical-align: top;
  }

  .col-container {
    position: relative;
    padding-right: 20px;

    @media (min-width: 640px) {
      padding-right: 0;
    }
  }

  .col .who {
    margin-bottom: 4px;
    white-space: nowrap;
  }

  .col .who,
  .col .when-date,
  .col .when-time {
    white-space: nowrap;
  }

  .col .when {
    min-width: 70px;
  }

  .col-actions {
    display: flex;
    box-sizing: border-box;
    flex-direction: row;
    align-items: center;
    place-content: space-between;
    position: absolute;
    padding: 0 8px;
    top: -2px;
    right: 0;
    height: 100%;
    min-height: 52px;

    @media (min-width: 640px) {
      display: none;
      height: 20px;
      min-height: auto;
      align-items: flex-start;
      background: linear-gradient(
        90deg,
        rgba(247, 247, 247, 0) 0%,
        rgba(247, 247, 247, 1) 33%,
        rgba(247, 247, 247, 1) 100%
      );
    }

    .icon-button {
      width: 24px;
      color: rgba(0, 0, 0, 0.67);

      &:not(.more) {
        display: none;
      }

      @media (min-width: 640px) {
        height: 20px;
        width: 20px;
        line-height: 20px;
        margin-left: 8px;

        > svg {
          margin: 0;
          height: 20px;
          width: 20px;
        }

        &:not(.more) {
          display: inline-block;
        }

        &.more {
          display: none;
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
    color: rgba(0, 0, 0, 0.34);

    p {
      width: 100%;
      margin: 8px 0;
      text-align: center;
    }
  }
</style>
