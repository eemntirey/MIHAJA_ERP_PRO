// src/contexts/CartContext.jsx
import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';

const CartContext = createContext();

const CART_STORAGE_KEY = 'erp_cart';

export const useCart = () => {
    const context = useContext(CartContext);
    if (!context) {
        throw new Error('useCart must be used within a CartProvider');
    }
    return context;
};

const getItemKey = (produit) => produit.id || produit.reference || produit._id;

export const CartProvider = ({ children }) => {
    const [cart, setCart] = useState([]);
    const { user } = useAuth();

    useEffect(() => {
        try {
            const stored = localStorage.getItem(CART_STORAGE_KEY);
            if (stored) {
                setCart(JSON.parse(stored));
            }
        } catch (e) {
            console.error('Erreur lecture panier:', e);
        }
    }, []);

    useEffect(() => {
        try {
            localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
        } catch (e) {
            console.error('Erreur ecriture panier:', e);
        }
    }, [cart]);

    const addItem = useCallback((produit, quantite = 1) => {
        const key = getItemKey(produit);
        setCart((prev) => {
            const existing = prev.find((item) => getItemKey(item) === key);
            if (existing) {
                return prev.map((item) =>
                    getItemKey(item) === key
                        ? { ...item, quantite: item.quantite + quantite }
                        : item
                );
            }
            return [...prev, { ...produit, quantite }];
        });
    }, []);

    const removeItem = useCallback((produit) => {
        const key = getItemKey(produit);
        setCart((prev) => prev.filter((item) => getItemKey(item) !== key));
    }, []);

    const updateQuantity = useCallback((produit, quantite) => {
        const key = getItemKey(produit);
        if (quantite <= 0) {
            removeItem(produit);
            return;
        }
        setCart((prev) =>
            prev.map((item) =>
                getItemKey(item) === key ? { ...item, quantite } : item
            )
        );
    }, []);

    const clearCart = useCallback(() => {
        setCart([]);
    }, []);

    const totalItems = cart.reduce((sum, item) => sum + item.quantite, 0);

    const totalPrice = cart.reduce(
        (sum, item) =>
            sum + Number(item.prix_vente_ht || item.prix || 0) * item.quantite,
        0
    );

    const value = {
        cart,
        addItem,
        removeItem,
        updateQuantity,
        clearCart,
        totalItems,
        totalPrice,
    };

    return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
};
