import React from 'react';
import { useAuth } from '../../contexts/AuthContext';

const NO_ACCESS_LABEL = 'non acces';

const AccessButton = ({
    permission,
    children,
    className,
    title,
    onClick,
    type = 'button',
    ...rest
}) => {
    const { hasPermission } = useAuth();
    const granted = !permission || hasPermission(permission);
    const noAccess = !granted;

    const handleClick = (e) => {
        if (noAccess) {
            e.preventDefault();
            e.stopPropagation();
            return;
        }
        if (onClick) onClick(e);
    };

    return (
        <button
            type={type}
            className={className}
            onClick={handleClick}
            disabled={noAccess || rest.disabled}
            aria-disabled={noAccess || rest.disabled}
            title={noAccess ? NO_ACCESS_LABEL : (title || rest.title)}
            {...rest}
        >
            {children}
        </button>
    );
};

export default AccessButton;
export { NO_ACCESS_LABEL };