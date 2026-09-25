// src/contexts/CartContext.jsx
import React, { createContext, useState, useContext, useEffect, useCallback, useMemo } from 'react';
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

const getItemKey = (produit) => produit.produit_id || produit.id || produit.reference || produit._id;

const getOwnerKey = (user) => {
    if (!user) return 'guest';
    return String(user.id || user.user_id || user.email || 'authenticated');
};

export const CartProvider = ({ children }) => {
    const { user } = useAuth();
    const storageKey = useMemo(
        () => `${CART_STORAGE_KEY}:${getOwnerKey(user)}`,
        [user]
    );

    const [cart, setCart] = useState([]);
    const [loadedStorageKey, setLoadedStorageKey] = useState(null);

    useEffect(() => {
        let nextCart = [];
        try {
            const stored = localStorage.getItem(storageKey);
            if (stored) {
                const parsed = JSON.parse(stored);
                nextCart = Array.isArray(parsed) ? parsed : [];
            }
        } catch (e) {
            console.error('Erreur lecture panier:', e);
        }
        setCart(nextCart);
        setLoadedStorageKey(storageKey);
    }, [storageKey]);

    useEffect(() => {
        // Ne jamais écrire le panier précédent sous la nouvelle clé avant
        // d'avoir chargé le panier du propriétaire courant.
        if (loadedStorageKey !== storageKey) return;
        try {
            localStorage.setItem(storageKey, JSON.stringify(cart));
        } catch (e) {
            console.error('Erreur écriture panier:', e);
        }
    }, [cart, storageKey, loadedStorageKey]);

    const addItem = useCallback((produit, quantite = 1) => {
        const key = getItemKey(produit);
        if (!key || quantite <= 0) return;
        setCart((prev) => {
            const existing = prev.find((item) => getItemKey(item) === key);
            if (existing) {
                return prev.map((item) =>
                    getItemKey(item) === key
                        ? { ...item, quantite: Number(item.quantite || 0) + quantite }
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
        const nextQuantity = Number(quantite);
        if (!Number.isFinite(nextQuantity) || nextQuantity <= 0) {
            removeItem(produit);
            return;
        }
        setCart((prev) =>
            prev.map((item) =>
                getItemKey(item) === key ? { ...item, quantite: nextQuantity } : item
            )
        );
    }, [removeItem]);

    const clearCart = useCallback(() => {
        setCart([]);
    }, []);

    const totalItems = cart.reduce((sum, item) => sum + Number(item.quantite || 0), 0);

    const totalPrice = cart.reduce(
        (sum, item) =>
            sum + Number(item.prix_vente_ht || item.prix || 0) * Number(item.quantite || 0),
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
