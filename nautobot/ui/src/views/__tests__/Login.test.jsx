import { render, screen } from '@testing-library/react';

import Login from '../Login';

describe('Login component', () => {
    it('renders the login form', () => {
        render(<Login />);
        screen.getByLabelText('Username');
        screen.getByLabelText('Password');
        screen.getByRole('button', { name: 'Log In' });
    });

    // TODO(timizuo): It would be nice to test for on submit of the login form
})


