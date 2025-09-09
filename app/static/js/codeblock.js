/**
 * CodeBlock tool for EditorJS with CodeMirror integration
 * Provides syntax-highlighted code editing with language selection
 */
class CodeBlock {
    constructor({ data, config, api, readOnly }) {
        this.api = api;
        this.readOnly = readOnly;
        this.config = config || {};
        
        this.data = {
            code: data.code || '',
            language: data.language || 'javascript',
            lineWrap: data.lineWrap !== undefined ? data.lineWrap : false
        };
        
        this.editor = null;
        this.wrapper = null;
        this.languageSelect = null;
        
        // Supported languages with their CodeMirror modes
        this.languages = {
            'javascript': { mode: 'javascript', label: 'JavaScript' },
            'python': { mode: 'python', label: 'Python' },
            'html': { mode: 'xml', label: 'HTML' },
            'css': { mode: 'css', label: 'CSS' },
            'json': { mode: 'application/json', label: 'JSON' },
            'sql': { mode: 'sql', label: 'SQL' },
            'bash': { mode: 'shell', label: 'Bash' },
            'php': { mode: 'php', label: 'PHP' },
            'java': { mode: 'text/x-java', label: 'Java' },
            'cpp': { mode: 'text/x-c++src', label: 'C++' },
            'csharp': { mode: 'text/x-csharp', label: 'C#' },
            'ruby': { mode: 'ruby', label: 'Ruby' },
            'go': { mode: 'go', label: 'Go' },
            'typescript': { mode: 'text/typescript', label: 'TypeScript' },
            'markdown': { mode: 'markdown', label: 'Markdown' },
            'xml': { mode: 'xml', label: 'XML' },
            'yaml': { mode: 'yaml', label: 'YAML' },
            'plaintext': { mode: null, label: 'Plain Text' }
        };
    }

    static get toolbox() {
        return {
            title: 'Code',
            icon: '<svg width="17" height="15" viewBox="0 0 17 15" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M1.83301 7.5L6.50033 11.6667M6.50033 3.33333L1.83301 7.5L6.50033 11.6667M15.1663 7.5L10.499 3.33333M10.499 11.6667L15.1663 7.5L10.499 3.33333" stroke="#4A4A4A" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        };
    }

    static get isReadOnlySupported() {
        return true;
    }

    render() {
        this.wrapper = document.createElement('div');
        this.wrapper.classList.add('codx-code-block');
        
        if (this.readOnly) {
            this.wrapper.classList.add('readonly');
        }
        
        // Prevent wrapper from losing focus to EditorJS
        this.wrapper.addEventListener('mousedown', (e) => {
            // Prevent event from bubbling to EditorJS
            e.stopPropagation();
        });
        
        this.wrapper.addEventListener('click', (e) => {
            e.stopPropagation();
        });
        
        // Create header with language selector
        const header = this.createHeader();
        this.wrapper.appendChild(header);
        
        // Create CodeMirror container
        const editorContainer = document.createElement('div');
        editorContainer.classList.add('codx-code-editor');
        this.wrapper.appendChild(editorContainer);
        
        // Initialize CodeMirror
        this.initializeCodeMirror(editorContainer);
        
        return this.wrapper;
    }

    createHeader() {
        const header = document.createElement('div');
        header.classList.add('codx-code-header');
        
        // Left side - Language selector
        const leftSide = document.createElement('div');
        leftSide.classList.add('codx-header-left');
        
        this.languageSelect = document.createElement('select');
        this.languageSelect.classList.add('codx-language-select');
        
        // Populate language options
        Object.entries(this.languages).forEach(([key, lang]) => {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = lang.label;
            option.selected = key === this.data.language;
            this.languageSelect.appendChild(option);
        });
        
        // Language change handler
        this.languageSelect.addEventListener('change', (e) => {
            this.data.language = e.target.value;
            this.updateEditorMode();
        });
        
        if (this.readOnly) {
            this.languageSelect.disabled = true;
        }
        
        leftSide.appendChild(this.languageSelect);
        
        // Right side - Action buttons
        const rightSide = document.createElement('div');
        rightSide.classList.add('codx-header-right');
        
        // Wrap toggle button
        const wrapButton = document.createElement('button');
        wrapButton.classList.add('codx-wrap-button');
        if (this.data.lineWrap) {
            wrapButton.classList.add('active');
        }
        wrapButton.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3,6 21,6"></polyline>
                <polyline points="3,12 15,12"></polyline>
                <polyline points="3,18 15,18"></polyline>
                <polyline points="18,15 21,18 18,21"></polyline>
            </svg>
        `;
        wrapButton.title = this.data.lineWrap ? 'Disable line wrap' : 'Enable line wrap';
        wrapButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.toggleLineWrap();
        });
        
        if (this.readOnly) {
            wrapButton.disabled = true;
        }
        
        // Copy button
        const copyButton = document.createElement('button');
        copyButton.classList.add('codx-copy-button');
        copyButton.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
        `;
        copyButton.title = 'Copy code';
        copyButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.copyCode();
        });
        
        rightSide.appendChild(wrapButton);
        rightSide.appendChild(copyButton);
        
        header.appendChild(leftSide);
        header.appendChild(rightSide);
        
        return header;
    }

    initializeCodeMirror(container) {
        const config = {
            value: this.data.code,
            lineNumbers: true,
            indentUnit: 4,
            tabSize: 4,
            lineWrapping: this.data.lineWrap,
            theme: 'default',
            readOnly: this.readOnly,
            matchBrackets: true,
            autoCloseBrackets: true,
            styleActiveLine: true,
            scrollbarStyle: 'native',
            viewportMargin: Infinity,
            extraKeys: {
                'Tab': (cm) => {
                    if (cm.somethingSelected()) {
                        cm.indentSelection('add');
                    } else {
                        cm.replaceSelection('    ');
                    }
                    return false;
                },
                'Shift-Tab': (cm) => {
                    cm.indentSelection('subtract');
                    return false;
                },
                'Ctrl-/': (cm) => {
                    this.toggleComment(cm);
                    return false;
                },
                'Cmd-/': (cm) => {
                    this.toggleComment(cm);
                    return false;
                },
                'Enter': (cm) => {
                    cm.execCommand('newlineAndIndent');
                    return false;
                },
                'Backspace': (cm) => {
                    if (cm.somethingSelected()) {
                        cm.replaceSelection('');
                    } else {
                        cm.execCommand('delCharBefore');
                    }
                    return false;
                },
                'Delete': (cm) => {
                    if (cm.somethingSelected()) {
                        cm.replaceSelection('');
                    } else {
                        cm.execCommand('delCharAfter');
                    }
                    return false;
                },
                'Ctrl-Backspace': (cm) => {
                    cm.execCommand('delGroupBefore');
                    return false;
                },
                'Ctrl-Delete': (cm) => {
                    cm.execCommand('delGroupAfter');
                    return false;
                },
                'Alt-Backspace': (cm) => {
                    cm.execCommand('delGroupBefore');
                    return false;
                },
                'Alt-Delete': (cm) => {
                    cm.execCommand('delGroupAfter');
                    return false;
                },
                'Home': (cm) => {
                    cm.execCommand('goLineStart');
                    return false;
                },
                'End': (cm) => {
                    cm.execCommand('goLineEnd');
                    return false;
                },
                'Ctrl-Home': (cm) => {
                    cm.execCommand('goDocStart');
                    return false;
                },
                'Ctrl-End': (cm) => {
                    cm.execCommand('goDocEnd');
                    return false;
                },
                'PageUp': (cm) => {
                    cm.execCommand('goPageUp');
                    return false;
                },
                'PageDown': (cm) => {
                    cm.execCommand('goPageDown');
                    return false;
                },
                'Up': (cm) => {
                    cm.execCommand('goLineUp');
                    return false;
                },
                'Down': (cm) => {
                    cm.execCommand('goLineDown');
                    return false;
                },
                'Left': (cm) => {
                    cm.execCommand('goCharLeft');
                    return false;
                },
                'Right': (cm) => {
                    cm.execCommand('goCharRight');
                    return false;
                },
                'Ctrl-Left': (cm) => {
                    cm.execCommand('goGroupLeft');
                    return false;
                },
                'Ctrl-Right': (cm) => {
                    cm.execCommand('goGroupRight');
                    return false;
                },
                'Shift-Up': (cm) => {
                    cm.execCommand('goLineUpSel');
                    return false;
                },
                'Shift-Down': (cm) => {
                    cm.execCommand('goLineDownSel');
                    return false;
                },
                'Shift-Left': (cm) => {
                    cm.execCommand('goCharLeftSel');
                    return false;
                },
                'Shift-Right': (cm) => {
                    cm.execCommand('goCharRightSel');
                    return false;
                },
                'Escape': () => {
                    // Prevent escape from bubbling up
                    return false;
                }
            }
        };
        
        // Set mode based on selected language
        const languageConfig = this.languages[this.data.language];
        if (languageConfig && languageConfig.mode) {
            config.mode = languageConfig.mode;
        }
        
        this.editor = CodeMirror(container, config);
        
        // Handle content changes
        this.editor.on('change', () => {
            this.data.code = this.editor.getValue();
        });
        
        // Prevent focus loss and ensure proper event handling
        this.editor.on('keydown', (cm, event) => {
            // Stop event propagation to prevent EditorJS from handling it
            event.stopPropagation();
        });
        
        this.editor.on('keyup', (cm, event) => {
            // Stop event propagation
            event.stopPropagation();
        });
        
        this.editor.on('keypress', (cm, event) => {
            // Stop event propagation
            event.stopPropagation();
        });
        
        // Handle focus events
        this.editor.on('focus', (cm) => {
            this.wrapper.classList.add('codx-focused');
            if (window.CODEBLOCK_DEBUG) {
                console.log('CodeMirror focused');
            }
        });
        
        this.editor.on('blur', (cm) => {
            // Small delay to check if focus moved within the code block
            setTimeout(() => {
                if (!this.wrapper.contains(document.activeElement)) {
                    this.wrapper.classList.remove('codx-focused');
                    if (window.CODEBLOCK_DEBUG) {
                        console.log('CodeMirror blurred, focus moved outside');
                    }
                } else {
                    if (window.CODEBLOCK_DEBUG) {
                        console.log('CodeMirror blurred, but focus still within wrapper');
                    }
                }
            }, 10);
        });
        
        // Handle click events to maintain focus
        container.addEventListener('mousedown', (e) => {
            e.stopPropagation();
        });
        
        container.addEventListener('click', (e) => {
            e.stopPropagation();
            if (this.editor && !this.readOnly) {
                this.editor.focus();
            }
        });
        
        // Prevent any key events from bubbling up from the container
        container.addEventListener('keydown', (e) => {
            e.stopPropagation();
        });
        
        container.addEventListener('keyup', (e) => {
            e.stopPropagation();
        });
        
        container.addEventListener('keypress', (e) => {
            e.stopPropagation();
        });
        
        // Auto-resize editor
        this.editor.setSize(null, 'auto');
        
        // Refresh editor after initialization
        setTimeout(() => {
            this.editor.refresh();
        }, 100);
    }

    toggleComment(cm) {
        const cursor = cm.getCursor();
        const line = cm.getLine(cursor.line);
        const commentMap = {
            'javascript': '//',
            'python': '#',
            'css': '/*',
            'html': '<!--',
            'sql': '--',
            'bash': '#',
            'php': '//',
            'java': '//',
            'cpp': '//',
            'csharp': '//',
            'ruby': '#',
            'go': '//',
            'rust': '//',
            'typescript': '//'
        };
        
        const commentChar = commentMap[this.data.language] || '//';
        
        if (line.trim().startsWith(commentChar)) {
            // Uncomment
            const newLine = line.replace(new RegExp(`^(\\s*)${commentChar.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s?`), '$1');
            cm.replaceRange(newLine, {line: cursor.line, ch: 0}, {line: cursor.line, ch: line.length});
        } else {
            // Comment
            const indentMatch = line.match(/^(\s*)/);
            const indent = indentMatch ? indentMatch[1] : '';
            const newLine = indent + commentChar + ' ' + line.slice(indent.length);
            cm.replaceRange(newLine, {line: cursor.line, ch: 0}, {line: cursor.line, ch: line.length});
        }
    }

    updateEditorMode() {
        if (!this.editor) return;
        
        const languageConfig = this.languages[this.data.language];
        if (languageConfig && languageConfig.mode) {
            this.editor.setOption('mode', languageConfig.mode);
        } else {
            this.editor.setOption('mode', null);
        }
    }

    save() {
        return {
            code: this.data.code,
            language: this.data.language
        };
    }

    static get sanitize() {
        return {
            code: false, // Don't sanitize code content
            language: false
        };
    }

    static get conversionConfig() {
        return {
            export: 'code', // Use 'code' property for export
            import: 'code'  // Use 'code' property for import
        };
    }

    // Handle EditorJS events
    rendered() {
        // Called when block is rendered
        if (this.editor) {
            setTimeout(() => {
                this.editor.refresh();
                if (!this.readOnly) {
                    this.editor.focus();
                }
            }, 100);
        }
    }

    // Prevent block deletion when user is editing
    validate(savedData) {
        return savedData.code !== undefined;
    }

    // Handle block selection
    selected() {
        if (this.editor && !this.readOnly) {
            this.editor.focus();
        }
        return true;
    }

    // Handle block deselection
    unselected() {
        // Allow deselection
        return true;
    }

    onPaste(event) {
        const content = event.clipboardData.getData('text/plain');
        if (content) {
            this.data.code = content;
            if (this.editor) {
                this.editor.setValue(content);
            }
        }
    }

    copyCode() {
        const code = this.data.code;
        
        if (navigator.clipboard && navigator.clipboard.writeText) {
            // Use modern clipboard API
            navigator.clipboard.writeText(code).then(() => {
                this.showCopyFeedback();
            }).catch(() => {
                this.fallbackCopy(code);
            });
        } else {
            // Fallback for older browsers
            this.fallbackCopy(code);
        }
    }

    fallbackCopy(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.top = '-9999px';
        textArea.style.left = '-9999px';
        document.body.appendChild(textArea);
        textArea.select();
        
        try {
            document.execCommand('copy');
            this.showCopyFeedback();
        } catch (err) {
            console.error('Failed to copy code:', err);
            this.showCopyError();
        } finally {
            document.body.removeChild(textArea);
        }
    }

    showCopyFeedback() {
        const copyButton = this.wrapper.querySelector('.codx-copy-button');
        if (copyButton) {
            const originalHTML = copyButton.innerHTML;
            copyButton.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20,6 9,17 4,12"></polyline>
                </svg>
            `;
            copyButton.classList.add('copied');
            
            setTimeout(() => {
                copyButton.innerHTML = originalHTML;
                copyButton.classList.remove('copied');
            }, 2000);
        }
    }

    showCopyError() {
        const copyButton = this.wrapper.querySelector('.codx-copy-button');
        if (copyButton) {
            copyButton.classList.add('error');
            setTimeout(() => {
                copyButton.classList.remove('error');
            }, 2000);
        }
    }

    toggleLineWrap() {
        if (!this.editor) return;
        
        const currentWrap = this.editor.getOption('lineWrapping');
        this.editor.setOption('lineWrapping', !currentWrap);
        
        // Update wrap button state
        const wrapButton = this.wrapper.querySelector('.codx-wrap-button');
        if (wrapButton) {
            if (!currentWrap) {
                wrapButton.classList.add('active');
                wrapButton.title = 'Disable line wrapping';
            } else {
                wrapButton.classList.remove('active');
                wrapButton.title = 'Enable line wrapping';
            }
        }
        
        // Refresh editor to apply changes
        setTimeout(() => {
            this.editor.refresh();
        }, 10);
    }
}