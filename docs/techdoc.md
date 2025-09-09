# General technical documentation

## Templates

We have two different base templates: `base.html` and `base_authenticated.html`. The `base.html` template is used for public-facing pages, while the `base_authenticated.html` template is used for pages that require user authentication.

We decided to approach the design differently than our previous implementation. We add sidebar to manage journal entries more effectively. At the center of the layout we display last modified entry so users can easily continue their work. Also to achieve better user experience we display recent 5 journal entries in the sidebar, also "More" button to redirect user to journal entries list page. Users can easily search for journal entries using the search bar located at the top of the sidebar.

We also add "Save" button at the top right corner of the layout, later auto-save functionality will be implemented.
We add a profile section at the bottom of the sidebar, where users can logout from account, view and edit their profile information.
At the top of the sidebar we add a "New Entry" button to allow users to quickly create a new journal entry.
At the bottom of the recent entries list, we add a "Tags" button so users can easily go to page to manage their tags.
Once user hovers on a journal entry in the sidebar, they will see three-dots button to open options, for now only delete. Later duplicate, "add to favorites" and "share" options will be implemented.

## User flow

1. User logs in and is redirected to the dashboard.
2. User can see the last modified entry in the center and recent entries in the sidebar.
3. User can create a new entry by clicking the "New Entry" button.
4. User can edit their profile information from the profile section.
5. User can manage their tags from the "Tags" button.
6. User can search for specific entries using the search bar.
7. User can save their changes by clicking the "Save" button.
8. User can view their profile information from the profile section.
9. User can logout from their account from the profile section.
