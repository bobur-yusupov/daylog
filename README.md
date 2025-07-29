# Daylog

------

A Django application for logging daily activities.

## Features

1. User authentication (registration, login, logout)
2. Journal entries (create, read, update, delete)
3. WYSIWYG (What You See Is What You Get) rich text editor support
4. View entries with filter/search by date, tags, and public/private status
5. Responsive design using Bootstrap
6. Tag management (create, read, delete tags)

## User flow

1. User registers an account.
2. User logs in to the application.
3. User can create a new journal entry by clicking "New Entry".
4. User fills out the entry form with a title and content in the WYSIWYG editor.
5. User can save the entry as public or private.
6. User can view a list of their journal entries on the dashboard.
7. User can filter entries by date range, tags, or public/private status.
8. User can edit or delete existing entries.
9. User can create and manage tags to categorize entries.
10. User can view individual entries with their content rendered from JSON to HTML.
11. User can log out of the application.

## Models

`User`: Extends Django's built-in User model for authentication.

`JournalEntry`:

- `user`: ForeignKey to the User model, linking each entry to its author.
- `title`: CharField for the title of the entry.
- `content`: JSONField for the content of the entry.
- `date`: DateTimeField for the date of the entry, defaulting to the current date and time.
- `is_public`: BooleanField to indicate if the entry is public or private.
- `tags`: ManyToManyField for associating tags with the entry, allowing for categorization.
- `created_at`: DateTimeField for when the entry was created, automatically set to the current date and time.
- `updated_at`: DateTimeField for when the entry was last updated, automatically set to the current date and time on save.

`Tag`:

- `user`: ForeignKey to the User model, linking each tag to its creator.
- `name`: CharField for the name of the tag, unique to prevent duplicates.
- `created_at`: DateTimeField for when the tag was created, automatically set to the current date and time.
- `updated_at`: DateTimeField for when the tag was last updated, automatically set to the current date and time on save.

## Core Views

- Home/Dashboard: Displays a list of journal entries with options to filter by date, tags, and public/private status. (paginated)
- Entry Detail: Displays a single journal entry with its content rendered from JSON to HTML.
- Create/Edit Entry: Form for creating and editing a journal entry with WYSIWYG content.

## Routes

- `/auth/register/`: User registration view.
- `/auth/login/`: User login view.
- `/auth/logout/`: User logout view.
- `/`: Home/Dashboard view showing all journal entries.
- `/entry/new/`: Form for creating a new journal entry.
- `/entry/<int:id>/`: View for a single journal entry.
- `/entry/<int:id>/edit/`: Form for editing an existing journal entry.
- `/tags/`: View for managing tags (creating, deleting).
- `/tags/new/`: Form for creating a new tag.
- `/tags/<int:id>/`: View for a specific tag.
- `/tags/<int:id>/delete/`: Route for deleting a specific tag.

## Tech Stack

Backend: Django (Python 3.11+)
Frontend: Django templates with Bootstrap for styling
Database: SQLite
Editor: Editor.js for WYSIWYG editing capabilities
Rendering: Content stored as JSON and rendered using the Editor.js Renderer library

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/bobur-yusupov/daylog.git
   cd daylog
   ```

2. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run migrations:

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. Create a superuser (optional):

   ```bash
   python manage.py createsuperuser
   ```

6. Start the development server:

   ```bash
   python manage.py runserver
   ```

## Usage

1. **User Registration/Login**: Navigate to `/register/` or `/login/` to create an account or sign in.

2. **Creating Entries**: Use the "New Entry" button to create journal entries with the WYSIWYG editor.

3. **Managing Tags**: Create and assign tags to categorize your entries for better organization.

4. **Filtering Entries**: Use the dashboard filters to view entries by date range, tags, or privacy status.

5. **Public/Private Entries**: Toggle entry visibility to share publicly or keep private.

## API Endpoints

### Authentication

- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout

### Journal Entries

- `GET /api/entries/` - List all entries (with filtering)
- `POST /api/entries/` - Create new entry
- `GET /api/entries/{id}/` - Get specific entry
- `PUT /api/entries/{id}/` - Update entry
- `DELETE /api/entries/{id}/` - Delete entry

### Tags

- `GET /api/tags/` - List user's tags
- `POST /api/tags/` - Create new tag
- `DELETE /api/tags/{id}/` - Delete tag

## API Authentication

DRF's token authentication is used for API endpoints. Include the token in the `Authorization` header as follows:

```plain
Authorization: Token <your_token>
```

## Pagination

The dashboard and API responses paginate journal entries with a default page size of 10 entries. Use the `page` query parameter to navigate between pages.

## Rendering Content

Journal entries store content as JSON generated by Editor.js. On the frontend, this JSON is parsed and rendered using the Editor.js Renderer library, which reconstructs the rich text layout in HTML.

## Testing

Use Django's built-in testing framework for testing the application.
Run tests using:

```bash
python manage.py test
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
