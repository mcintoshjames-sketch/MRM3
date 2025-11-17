import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test/utils';
import LoginPage from './LoginPage';

// Mock the AuthContext
const mockLogin = vi.fn();
vi.mock('../contexts/AuthContext', () => ({
    useAuth: () => ({
        login: mockLogin,
        user: null,
        logout: vi.fn(),
        loading: false,
    }),
}));

describe('LoginPage', () => {
    beforeEach(() => {
        mockLogin.mockReset();
    });

    it('renders login form with all fields', () => {
        render(<LoginPage />);

        expect(screen.getByLabelText('Email')).toBeInTheDocument();
        expect(screen.getByLabelText('Password')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Login' })).toBeInTheDocument();
    });

    it('shows default credentials hint', () => {
        render(<LoginPage />);

        expect(screen.getByText(/admin@example.com/)).toBeInTheDocument();
    });

    it('allows typing in email and password fields', async () => {
        render(<LoginPage />);

        const emailInput = screen.getByLabelText('Email') as HTMLInputElement;
        const passwordInput = screen.getByLabelText('Password') as HTMLInputElement;

        fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
        fireEvent.change(passwordInput, { target: { value: 'password123' } });

        expect(emailInput.value).toBe('test@example.com');
        expect(passwordInput.value).toBe('password123');
    });

    it('calls login on form submit', async () => {
        mockLogin.mockResolvedValueOnce(undefined);
        render(<LoginPage />);

        fireEvent.change(screen.getByLabelText('Email'), {
            target: { value: 'test@example.com' }
        });
        fireEvent.change(screen.getByLabelText('Password'), {
            target: { value: 'password123' }
        });
        fireEvent.click(screen.getByRole('button', { name: 'Login' }));

        await waitFor(() => {
            expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123');
        });
    });

    it('displays error message on failed login', async () => {
        mockLogin.mockRejectedValueOnce({
            response: { data: { detail: 'Invalid credentials' } }
        });
        render(<LoginPage />);

        fireEvent.change(screen.getByLabelText('Email'), {
            target: { value: 'wrong@example.com' }
        });
        fireEvent.change(screen.getByLabelText('Password'), {
            target: { value: 'wrongpass' }
        });
        fireEvent.click(screen.getByRole('button', { name: 'Login' }));

        await waitFor(() => {
            expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
        });
    });

    it('shows generic error when no detail provided', async () => {
        mockLogin.mockRejectedValueOnce(new Error('Network error'));
        render(<LoginPage />);

        fireEvent.change(screen.getByLabelText('Email'), {
            target: { value: 'test@example.com' }
        });
        fireEvent.change(screen.getByLabelText('Password'), {
            target: { value: 'password123' }
        });
        fireEvent.click(screen.getByRole('button', { name: 'Login' }));

        await waitFor(() => {
            expect(screen.getByText('Login failed')).toBeInTheDocument();
        });
    });

    it('has required email and password fields', () => {
        render(<LoginPage />);

        expect(screen.getByLabelText('Email')).toBeRequired();
        expect(screen.getByLabelText('Password')).toBeRequired();
    });

    it('email input has correct type', () => {
        render(<LoginPage />);

        expect(screen.getByLabelText('Email')).toHaveAttribute('type', 'email');
    });

    it('password input has correct type', () => {
        render(<LoginPage />);

        expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password');
    });
});
